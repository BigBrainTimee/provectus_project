# Claude Code Usage Analytics Platform

## Project Overview

This project implements an end-to-end analytics platform that processes telemetry data from Claude Code sessions and transforms it into actionable insights about developer behavior.

The system ingests raw telemetry event streams, processes and validates the data, stores it in a structured database, and provides analytics through an interactive dashboard.

The goal of the project is to demonstrate skills in:

- Data processing pipelines
- Database design
- Analytics and insight generation
- Data visualization
- AI-assisted software development

The platform follows an **AI-first development approach**, leveraging LLM tools such as Cursor and ChatGPT to accelerate implementation and improve development productivity.

---

# System Architecture

The system is organized into several layers:

### 1. Data Ingestion
Raw telemetry data is loaded from JSON and CSV datasets.

### 2. Data Validation
Incoming telemetry events are validated to ensure correct structure and required fields.

### 3. Data Transformation
Raw events are normalized and structured into a format suitable for analytics.

### 4. Data Storage
Processed data is stored in a SQLite database using a normalized schema with optimized indexes.

Main database tables:

- `employees`
- `sessions`
- `events`
- `token_usage`

### 5. Analytics Layer
An `AnalyticsService` module performs analytical queries on the stored data to extract usage insights.

### 6. Visualization
A Streamlit dashboard presents insights using interactive charts and metrics.

---

# Features

The analytics platform provides insights such as:

- Token consumption trends by user role
- Token usage by project type
- Peak usage hours and developer activity patterns
- Most common code generation events
- Session behavior statistics
- Most active users and tools

The dashboard allows interactive exploration of the data using filters and dynamic charts.

---

# Technologies Used

- **Python**
- **SQLite**
- **Pandas**
- **Streamlit**
- **Plotly**
- **NumPy**

---

# Project Structure
