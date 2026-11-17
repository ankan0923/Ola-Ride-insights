# OLA Ride Insights \| Ride-Sharing Business Analytics

An end-to-end business intelligence project that analyzes OLA
ride-booking data to understand demand patterns, revenue performance,
vehicle utilization, cancellations, customer and driver ratings, and
operational opportunities.

The project combines **SQL, Power BI, Python, and Streamlit** to turn
raw ride-booking records into interactive dashboards, query-based
analysis, and business recommendations.

------------------------------------------------------------------------

## 1. Project Overview

Ride-sharing platforms generate data about bookings, ride status, driver
availability, fares, payment methods, locations, and customer
experience. Analyzing this data can help identify operational
bottlenecks and opportunities to improve service quality and business
performance.

**OLA Ride Insights** explores these areas through data preprocessing,
SQL analysis, Power BI reporting, and an interactive Streamlit
application.

  Project detail   Description
  ---------------- ---------------------------------------------------
  Project name     OLA Ride Insights
  Domain           Ride-Sharing & Mobility Analytics
  Project type     End-to-end Data Analytics / Business Intelligence
  Core tools       Python, SQL, Power BI, Streamlit
  Main libraries   Pandas, NumPy, Plotly
  Dataset          OLA ride-booking dataset

## 2. Business Problem

The business needs a clear view of ride demand, successful and
unsuccessful bookings, revenue, driver availability, vehicle
performance, and customer experience. Without a consolidated analytical
view, it can be difficult to identify peak-demand periods, understand
cancellation reasons, detect unusual patterns, and prioritize
operational improvements.

This project analyzes OLA ride data and presents findings through SQL
queries, interactive Power BI dashboards, and a Streamlit analytics
application.

## 3. Business Objectives and Use Cases

-   Identify peak demand hours and support better driver allocation.
-   Analyze booking patterns and customer behavior.
-   Understand revenue by payment method, vehicle type, and pickup
    location.
-   Investigate customer-side and driver-side cancellations.
-   Monitor driver and customer ratings.
-   Identify unusual values and potential operational anomalies for
    further review.
-   Convert analytical findings into practical business recommendations.

## 4. Project Workflow

1.  **Data understanding and exploration** --- inspect the dataset,
    columns, data types, booking statuses, payment methods, and ratings.
2.  **Data cleaning and preprocessing** --- handle missing and
    inconsistent values, standardize data types, remove duplicate
    booking IDs, and create time-based features.
3.  **SQL analysis** --- answer project questions and additional
    business questions using queries.
4.  **Power BI dashboard** --- present ride trends, vehicle performance,
    revenue, cancellations, and ratings with interactive filtering.
5.  **Streamlit application** --- provide interactive analytics, SQL
    query execution, dashboard viewing, anomaly analysis,
    recommendations, and data exploration.
6.  **Business interpretation** --- use the results to identify
    operational issues and improvement opportunities.

## 5. Technology Stack

  Technology       Purpose
  ---------------- --------------------------------------------------
  Python           Data processing and application development
  Pandas           Data cleaning, transformation, and aggregation
  NumPy            Numerical operations
  SQL              Business queries and analytical summaries
  SQLite           SQL engine used inside the Streamlit application
  Power BI         Interactive business intelligence dashboards
  Streamlit        Interactive web application
  Plotly           Interactive charts and visualizations
  Git and GitHub   Version control and project documentation

> The Streamlit application's SQL engine is SQLite, built in memory from
> the cleaned dataset. The project documentation also references MySQL
> as a project database option. The application notes explain the SQL
> dialect differences where relevant.

## 6. Data Cleaning and Preprocessing

The application's data-processing logic is implemented in
`ola_logic.py`.

The cleaning workflow includes:

-   Standardizing column names by trimming whitespace and replacing
    spaces with underscores.
-   Validating the presence of required columns.
-   Converting text values such as `"null"` into proper missing values.
-   Converting the booking date to a datetime data type and removing
    rows with invalid dates.
-   Converting relevant numeric columns, including booking value, ride
    distance, turnaround times, and ratings.
-   Filling missing cancellation reasons, incomplete-ride labels, and
    payment methods with appropriate labels such as `Not Applicable` and
    `No Payment`.
-   Setting zero ride distance to missing for bookings that were not
    successful, because no actual ride distance exists for those
    bookings.
-   Removing duplicate records using `Booking_ID`.
-   Creating derived time features:
    -   `Ride_Date`
    -   `Hour`
    -   `Day`
    -   `Weekday`
    -   `Is_Weekend`
    -   `Time_Bucket`

Missing ride-related values are retained where they are not applicable,
rather than being filled with artificial values that could distort
averages.

### Required dataset columns

The application validates these core fields:

`Date`, `Booking_ID`, `Booking_Status`, `Customer_ID`, `Vehicle_Type`,
`Pickup_Location`, `Drop_Location`, `Booking_Value`, `Ride_Distance`.

Other available columns are used for additional analysis, including
payment method, cancellation reasons, incomplete-ride information, and
driver/customer ratings.

## 7. SQL Analysis

The application provides two sets of predefined SQL questions and a
custom SQL playground.

### A. Project SQL questions

1.  Retrieve all successful bookings.
2.  Find the average ride distance for each vehicle type.
3.  Get the total number of cancelled rides by customers.
4.  List the top five customers by number of rides.
5.  Count driver cancellations due to personal and car-related issues.
6.  Find maximum and minimum driver ratings for Prime Sedan bookings.
7.  Retrieve rides paid for using UPI.
8.  Find the average customer rating per vehicle type.
9.  Calculate the total booking value of successful rides.
10. List incomplete rides with their reasons.

### B. Additional business SQL questions

1.  Cancellation rate by vehicle type.
2.  Peak demand hours.
3.  Unmet demand: Driver Not Found bookings by pickup area.
4.  Booking value associated with unsuccessful bookings.
5.  Revenue per kilometre by vehicle type.
6.  Repeat customers with more than one successful ride.
7.  Payment-method share of successful rides.
8.  Top five pickup locations by revenue.
9.  Low-rated drivers by vehicle type.
10. Highest-revenue days.

### C. SQL Playground

Users can write and execute their own SQL queries on the `ola_rides`
table.

-   Read-only `SELECT` and `WITH` queries.
-   One statement per execution.
-   Maximum of 5,000 returned rows.
-   Query timeout of 10 seconds.
-   Recent query history.
-   CSV download of query results.
-   Optional charting for suitable query outputs.

The playground is intentionally read-only; data-changing SQL statements
are blocked.

## 8. Power BI Dashboard

The Power BI dashboard is organized around five analytical views.

  -----------------------------------------------------------------------
  Dashboard section                   Analysis
  ----------------------------------- -----------------------------------
  Overall                             Ride volume over time and booking
                                      status breakdown

  Vehicle Type                        Top vehicle types by ride distance

  Revenue                             Revenue by payment method, top
                                      customers by booking value, and
                                      ride-distance patterns

  Cancellation                        Customer and driver cancellation
                                      reasons

  Ratings                             Driver ratings and customer ratings
  -----------------------------------------------------------------------

The dashboard is intended to support interactive exploration through
filters and slicers, with KPIs and visualizations focused on business
performance.

> Add your Power BI dashboard screenshots or published report link to
> this section when preparing the public GitHub repository.

## 9. Streamlit Application
**[Explore the live dashboard](https://mainpy-scwdc2hvijqn4vdd3vbi5z.streamlit.app/)**

The Streamlit application is named **OLA Ride Insights** and uses a dark
analytical interface with interactive Plotly charts.

### Application pages and capabilities

  -----------------------------------------------------------------------
  Page                                Features
  ----------------------------------- -----------------------------------
  Overview                            Main KPIs, booking status, daily
                                      booking trends, and key findings

  Overall                             Ride volume, booking status, hourly
                                      and weekday demand, and demand
                                      heatmap

  Vehicle Type                        Vehicle-level bookings, distance,
                                      cancellation,
                                      revenue-per-kilometre, and ratings

  Revenue                             Revenue by payment method, top
                                      customers, pickup locations, and
                                      daily revenue

  Cancellation                        Customer and driver cancellation
                                      reasons, hourly cancellation rate,
                                      and driver-not-found areas

  Ratings                             Driver and customer rating analysis

  SQL Queries                         Predefined project and business
                                      queries

  SQL Playground                      Custom read-only SQL execution,
                                      query history, result charts, and
                                      CSV export

  Power BI Dashboard                  View uploaded Power BI dashboard
                                      images

  Insights & Anomalies                Analytical flags and unusual
                                      patterns for review

  Recommendations                     Data-driven operational
                                      recommendations

  Forecast                            Forecasting functionality provided
                                      by the application

  Data Explorer                       Search, filter, inspect, and export
                                      selected data

  About & Data Quality                Cleaning methodology, remaining
                                      missing values, and data dictionary
  -----------------------------------------------------------------------

### Interactive features

-   Upload a raw or cleaned CSV file.
-   Automatically clean uploaded data.
-   Filter by date range, vehicle type, and booking status.
-   Explore interactive Plotly visualizations.
-   Run predefined and custom SQL queries.
-   Download query results and filtered data as CSV.
-   View Power BI dashboard images from the configured dashboard-images
    folder.
-   Review analytical insights and recommendations.

## 10. Key Performance Indicators

The application calculates KPIs from the currently selected dataset and
filters, including:

-   Total bookings
-   Successful bookings and success rate
-   Customer and driver cancellations
-   Cancellation rate
-   Driver-not-found bookings and rate
-   Revenue from successful rides
-   Booking value associated with unsuccessful bookings
-   Average fare
-   Average ride distance
-   Average driver rating
-   Average customer rating
-   Unique customers

**Metric interpretation:** The application calculates revenue using
successful bookings only. Its unsuccessful-booking value metric sums
booking values for records whose status is not `Success`; it represents
booking value associated with unsuccessful bookings, not necessarily
realized financial loss.

## 11. Business Insights and Recommendations

The application is designed to surface findings that can support actions
such as:

-   Improving driver acceptance and reducing repeated driver-side
    cancellations.
-   Positioning drivers in pickup areas with a high number of Driver Not
    Found bookings.
-   Reviewing common customer cancellation reasons and improving pickup
    communication.
-   Investigating unusual revenue-per-kilometre patterns across vehicle
    types.
-   Reviewing customers with repeated cancellations.
-   Examining unusually high fares and significant differences between
    driver and customer ratings.

Recommendations and anomaly flags are analytical indicators for
investigation. They should be validated with operational context before
business action is taken.

## 12. Project Structure

A suggested GitHub repository structure is:

``` text
OLA-Ride-Insights/
│
├── main.py                  # Streamlit user interface
├── ola_logic.py             # Data cleaning, KPIs, SQL, insights and logic
├── ola_cleaned.csv          # Cleaned dataset (if permitted to share)
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
│
├── logo/                    # OLA and vehicle images
├── dashboard_images/        # Power BI dashboard screenshots
│
├── power_bi/
│   └── OLA_Ride_Insights.pbix
│
└── sql/
    └── ola_queries.sql      # Optional standalone SQL script
```

This is a suggested structure. Include only the folders and files that
exist in your final repository.

## 13. Installation and Execution

### Prerequisites

-   Python 3.10 or a compatible Python version.
-   pip.
-   A raw or cleaned OLA CSV dataset.

### Step 1: Clone the repository

``` bash
git clone https://github.com/your-username/OLA-Ride-Insights.git
cd OLA-Ride-Insights
```

### Step 2: Install dependencies

Create a `requirements.txt` file containing the packages used by the
application:

``` text
streamlit
pandas
numpy
plotly
Pillow
```

Install them:

``` bash
pip install -r requirements.txt
```

### Step 3: Add the dataset

Place `ola_cleaned.csv` in the same directory as `main.py`, or upload a
raw/cleaned CSV using the application's **Data source** option.

The application searches for `ola_cleaned.csv` first and then for
another CSV file in its application directory.

### Step 4: Run the application

``` bash
streamlit run main.py
```

Streamlit will provide a local URL in the terminal, normally:

``` text
http://localhost:8501
```

## 14. Data and Usage Notes

-   The application requires the core columns listed in the
    data-cleaning section.
-   Raw CSV files are cleaned when loaded; already-cleaned files are
    passed through the same cleaning function.
-   The SQL playground uses an in-memory SQLite database created from
    the loaded dataset.
-   The Power BI page uses dashboard images stored in
    `dashboard_images/`.
-   OLA logos and vehicle images can be placed in the configured image
    folder (`logo/`, `Logo/`, `logos/`, or `assets/`).
-   Do not commit confidential, personal, or otherwise restricted data
    to a public repository. Check the dataset's usage and redistribution
    terms before publishing it.

## 15. Project Outcomes

The project brings together data preprocessing, SQL querying,
interactive dashboarding, and application development to provide a
consolidated view of ride-sharing operations.

It supports: - Faster exploration of booking and demand patterns. -
Easier analysis of revenue, cancellations, vehicle performance, and
ratings. - Reusable SQL analysis for common business questions. -
Interactive access to data and query results. - Evidence-based
recommendations for operational improvement.

## 16. Future Improvements

-   Publish the Streamlit application to a hosting platform.
-   Add automated data refresh and scheduled reporting.
-   Connect the application to a production database where appropriate.
-   Add role-based access and stronger deployment security.
-   Validate forecasts against a held-out time period and report
    forecast error.
-   Extend analysis with driver utilization, customer retention, and
    location-level demand studies.

## 17. Author

**Ankan Chowdhury**

Data Analytics \| SQL \| Power BI \| Python \| Streamlit

------------------------------------------------------------------------

*If you find this project useful, feel free to explore the code,
dashboards, and analytical workflow.*
