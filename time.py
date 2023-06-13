import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(
    page_title="Time Tracking",
    page_icon="🧊",
    layout="wide"
)

# Function to perform some algorithms on the data
def perform_algorithms(data):
    # Convert Von and Bis columns to datetime
    data['Von'] = pd.to_datetime(data['Von'])
    data['Bis'] = pd.to_datetime(data['Bis'])

    # Format Von and Bis columns as DD-MM-YY Hours:Minutes
    data['Startzeit'] = data['Von'].dt.strftime('%d-%m-%y %H:%M')
    data['Endzeit'] = data['Bis'].dt.strftime('%d-%m-%y %H:%M')

    # Extract Meeting status from Beschreibung
    def extract_meeting_status(description):
        if pd.isna(description):
            return ''
        description = str(description)
        if 'Meeting: Ja Nein' in description:
            return 'Nein'
        if 'Meeting: Ja' in description:
            return 'Ja'
        if 'Meeting: Nein' in description:
            return 'Nein'
        if 'Meeting:  Nein' in description:
            return 'Nein'
        return ''

    data['Meeting'] = data['Beschreibung'].apply(extract_meeting_status)

    # Map Projekt codes to full names
    project_mapping = {
        "PLAN": "Planung & Dokumentation",
        "AT": "Academy Tasks",
        "AV": "Academy Videos",
        "HT": "Helpdesk Tasks",
        "HA": "Helpdesk Artikel",
        "MEET": "Meetings: Daily & Weekly & POs"
    }
    data['Projekt'] = data['Projekt'].map(project_mapping)

    # Extract Academy and Helpdesk percentages
    def extract_percentages(description):
        if not isinstance(description, str):
            return 0, 0

        academy_pct = re.search(r'Academy: (\d+)%', description)
        helpdesk_pct = re.search(r'Helpdesk: (\d+)%', description)
        academy_pct = int(academy_pct.group(1)) if academy_pct else 0
        helpdesk_pct = int(helpdesk_pct.group(1)) if helpdesk_pct else 0
        return academy_pct, helpdesk_pct

    data['Academy_pct'], data['Helpdesk_pct'] = zip(*data['Beschreibung'].apply(extract_percentages))

    # Split the rows and adjust the Dauer column
    def split_row(row):
        academy_pct = row['Academy_pct']
        helpdesk_pct = row['Helpdesk_pct']
        dauer = float(row['Dauer'])

        rows = []
        if academy_pct > 0:
            academy_dauer = dauer * (academy_pct / 100)
            new_row = row.copy()
            new_row['Dauer'] = round(academy_dauer, 2)
            new_row['Task_Type'] = 'Academy'
            rows.append(new_row)

        if helpdesk_pct > 0:
            helpdesk_dauer = dauer * (helpdesk_pct / 100)
            new_row = row.copy()
            new_row['Dauer'] = round(helpdesk_dauer, 2)
            new_row['Task_Type'] = 'Helpdesk'
            rows.append(new_row)

        return rows

    # Split rows
    new_data = []
    for index, row in data.iterrows():
        new_data.extend(split_row(row))

    # Create the final DataFrame
    final_data = pd.DataFrame(new_data)

    # Drop unwanted columns
    final_data = final_data.drop(columns=["Beschreibung", "Startzeit", "Endzeit", "Helpdesk_pct", "Academy_pct"])

    # Rename Task_Type column to Abteilung
    final_data = final_data.rename(columns={"Task_Type": "Abteilung"})

    # Return the modified DataFrame
    return final_data

# Title of the page
st.title('CSV File Processor')

# Upload CSV file
file = st.file_uploader("Choose a CSV file", type="csv")

# Placeholder for displaying data table
data_placeholder = st.empty()


# ...

# Process the uploaded file
if file:
    data = pd.read_csv(file)

    # Perform algorithms on data
    data = perform_algorithms(data)

    # Individual filters
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Capture filter values
    search_aufgabe = col1.text_input("Aufgabe", "").strip()
    search_von = col2.date_input("Von", value=data['Von'].min())
    search_bis = col3.date_input("Bis", value=datetime.now().date())

    # Convert search_bis to datetime with time set to 23:59
    search_bis = pd.to_datetime(search_bis) + pd.DateOffset(hours=23, minutes=59)

    search_projekt = col4.selectbox("Projekt", [""] + data['Projekt'].unique().tolist())
    search_meeting = col5.selectbox("Meeting", ["", "Ja", "Nein"])
    search_abteilung = col6.selectbox("Abteilung", ["", "Academy", "Helpdesk"])

    # Apply filters
    if search_aufgabe:
        data = data[data['Aufgabe'].apply(lambda x: str(x).strip()).str.contains(search_aufgabe, case=False, na=False)]

    if search_von:
        data = data[data['Von'] >= pd.to_datetime(search_von)]

    if search_bis:
        data = data[data['Bis'] <= search_bis]

    if search_projekt:
        data = data[data['Projekt'] == search_projekt]

    if search_meeting:
        data = data[data['Meeting'] == search_meeting]

    if search_abteilung:
        data = data[data['Abteilung'] == search_abteilung]

    # Display data in a table
    data_placeholder.dataframe(data)

    # Display the sum of the "Dauer" column
    sum_dauer = round(data['Dauer'].sum(), 2)
    st.subheader(f'**Dauer ingesamt (in h):** {sum_dauer}')

    # Placeholder for displaying charts divided into three columns
    col_chart1, col_chart2, col_chart3 = st.columns(3)

    # Pie chart creation showing the ratio between Helpdesk and Academy
    abteilung_data = data.groupby('Abteilung')['Dauer'].sum().reset_index()
    if not abteilung_data.empty:
        fig1 = px.pie(abteilung_data, names='Abteilung', values='Dauer', title='Helpdesk & Academy')
        col_chart1.plotly_chart(fig1)
    else:
        col_chart1.write('No data available for chart.')

    # Pie chart creation showing the ratio between different projects
    projekt_data = data.groupby('Projekt')['Dauer'].sum().reset_index()
    if not projekt_data.empty:
        fig2 = px.pie(projekt_data, names='Projekt', values='Dauer', title='Projekte')
        col_chart2.plotly_chart(fig2)
    else:
        col_chart2.write('No data available for chart.')

    # Pie chart creation showing the ratio of Meeting status
    meeting_data = data.groupby('Meeting')['Dauer'].sum().reset_index()
    if not meeting_data.empty:
        fig3 = px.pie(meeting_data, names='Meeting', values='Dauer', title='Meeting Status')
        col_chart3.plotly_chart(fig3)
    else:
        col_chart3.write('No data available for chart.')

