
import streamlit as st 
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date 
import pandas as pd 
import os
import json 

SHEET_NAME = "VentureExpenses"
HEADERS = ["Date", "Venture", "Category", "Detail", "Final Amount (AD)"]

# Google Sheets auth
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_sheets_key"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict,scope)
    return gspread.authorize(creds)

# Get or initialize the sheet
def get_sheet():
    client = get_gsheet_client()
    sheet = client.open(SHEET_NAME).sheet1
    first_row = sheet.row_values(1)
    if not first_row or first_row != HEADERS:
        sheet.clear()
        sheet.insert_row(HEADERS, 1)
    return sheet    

# Append new record
def append_to_sheet(record):
    sheet = get_sheet()
    sheet.append_row(record)

# Fetch all records into a DataFrame
def fetch_records():
    sheet = get_sheet()
    values = sheet.get_all_values()

    if not values or len(values) < 2:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(values[1:],columns=values[0])
    return df
    #data = sheet.get_all_records()
    #if not data:
    #    return pd.DataFrame(columns=HEADERS) 
    #return pd.DataFrame(data)

# STREAMLIT UI
st.title("Venture Expense Tracker")

with st.form("entry_form"):
    st.subheader("Add New Entry")

    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("Date", value=date.today())
        venture = st.selectbox("Venture", [
            "Venture 1 : AI Tools",
            "Venture 2 : KanoonAI",
            "Venture 3 : Idli Bundi"
        ])
    
    with col2:
        category = st.selectbox("Category", ["Subscription", "Operating", "Marketing", "Misc", "Emp"])
        detail = st.text_input("Detail")
        f_amount = st.number_input("Final Amount (AD)", step=1.0)

    submitted = st.form_submit_button("Submit Expense")
    if submitted and venture:
        new_record = [
            entry_date.strftime("%d/%m/%Y"),
            venture,
            category,
            detail,
            f_amount
        ]
        append_to_sheet(new_record)
        st.success("Expense added successfully to Sheets!")

# Manual Refresh Button
if st.button("Refresh Records"):
    st.rerun()

# View Records
st.subheader("View Transaction Records")
df = fetch_records()
df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

if not df.empty:
    selected_venture = st.selectbox("Filter by Venture", ["All"] + sorted(df["Venture"].unique()))
    filtered_df = df if selected_venture == "All" else df[df["Venture"] == selected_venture]

    st.write("Expense Records:")
    st.dataframe(filtered_df.set_index(pd.Index(range(1, len(filtered_df) + 1))))

    total_filtered = filtered_df["Final Amount (AD)"].sum()
    if selected_venture == "All":
        pass
        #st.write(f"Grand Total for all ventures: {total_filtered:,.2f}")
    else:
        st.write(f"Total for {selected_venture}: {total_filtered:,.2f}")

    st.write("Venture-wise Totals:")
    summary_df = df.groupby("Venture")["Final Amount (AD)"].sum().reset_index()
    summary_df.columns = ["Venture", "Total"]
    st.table(summary_df.style.format({"Total": "{:,.2f}"}))

    grand_total = df["Final Amount (AD)"].sum()
    st.write(f"Grand Total for all ventures: {grand_total:,.2f}")
else:
    st.info("No records found. Start by adding an expense.")

# Updating / Deleting Entries
st.subheader("Update / Delete Transaction")
if not df.empty:
    venture_filter = st.selectbox("Select Venture", sorted(df["Venture"].unique()))
    filtered_df = df[df["Venture"] == venture_filter]

    category_filter = st.selectbox("Select Category", sorted(filtered_df["Category"].unique()))
    filtered_df = filtered_df[filtered_df["Category"] == category_filter]
    
    if filtered_df.empty:
        st.warning("No matching entries found.")
    else:
        selected_index = st.selectbox("Select entry to update/delete", options=filtered_df.index, format_func=lambda i: f"{i+1}) {filtered_df.loc[i,'Detail']}  {filtered_df.loc[i,'Final Amount (AD)']}")

        if selected_index is not None:
            selected_row = df.loc[selected_index]

            with st.expander("Update This Entry"):
                with st.form("update_form"):
                    new_date = st.date_input("Date", value=pd.to_datetime(selected_row["Date"]))
                    new_venture = st.selectbox("Venture", df["Venture"].unique(), index=list(df["Venture"].unique()).index(selected_row["Venture"]))
                    new_category = st.selectbox("Category", df["Category"].unique(), index=list(df["Category"].unique()).index(selected_row["Category"]))
                    new_detail = st.text_input("Detail", value=selected_row["Detail"])
                    new_amount = st.number_input("Final Amount (AD)", step=1.0, value=float(selected_row["Final Amount (AD)"]))

                    if st.form_submit_button("Update Entry"):
                        sheet = get_sheet()
                        updated_row = [
                            new_date.strftime("%d/%m/%Y"),
                            new_venture,
                            new_category,
                            new_detail,
                            new_amount
                        ]
                        sheet.update(f"A{selected_index + 2}:E{selected_index + 2}", [updated_row])
                        st.success("Entry updated. Please refresh.")

            with st.expander("Delete This Entry"):
                if st.button("Delete Entry"):
                    sheet = get_sheet()
                    sheet.delete_rows(selected_index + 2)
                    st.warning("Entry deleted. Please refresh.")
