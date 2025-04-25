# AMI System (UWM Capstone Project)

Air Monitoring Interface System is a sensor data monitoring platform used by a team for the UWM Capstone Project. It is a Django-based web application used to receive, store, visualize, and export data from various environmental sensors.

## Key Features

*   **Data Reception**: Provides API endpoints to receive data from sensors (Temperature, Humidity, CO2, PM1.0, PM2.5, PM10.0).
*   **Data Query**: Provides a RESTful API to query stored sensor data (requires user login), supporting filtering by time range.
*   **Data Export**: Allows logged-in users to export data for specified time ranges and sensor types as CSV or JSON files.
*   **User Authentication**: Includes user registration, login, and logout functionalities.
*   **Gmail Notifications**: Sends notifications when thresholds are exceeded.
*   **Data Visualization**: Provides charts or other forms to display sensor data trends.
*   **Chatbot**: Integrates multiple chatbots, offering free or paid features.

## Technology Stack

*   **Backend**: Python, Django, Django REST Framework
*   **Database**: SQLite
*   **Frontend**: HTML, CSS, JavaScript
*   **AI Features**: MCP (Model Context Protocol technology, used for DeepSeek AI), Hybrid Strategy Answering technology (used for basic AI)

## Installation and Running

1.  **Clone Repository**:
    ```bash
    git clone https://github.com/panhyer36/sensor_monitor.git
    cd sensor_monitor
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**:
    The project currently lacks a `requirements.txt` file. You need to manually install dependencies based on `INSTALLED_APPS` in `config/settings.py` and `import` statements in the code. Key dependencies include:
    ```bash
    pip install django djangorestframework python-dotenv mcp mcpo openai # Other dependencies might be needed
    ```

4.  **Database Migration**:
    ```bash
    python manage.py migrate
    ```

5.  **Create Admin User**:
    You can use the provided script:
    ```bash
    python create_admin.py
    ```
    Or use the Django command:
    ```bash
    python manage.py createsuperuser
    ```

6.  **Configure Google Mail API Key**
    (You will need to set up API credentials in `config/settings.py`)

7.  **Run Development Server**:
    You need to run two processes, preferably in separate terminals:
    ```bash
    # Terminal 1: Run Django development server
    python manage.py runserver
    ```
    ```bash
    # Terminal 2: Run MCP server
    mcpo --host 127.0.0.1 --port 8002 -- python MCP_server/mcp_server.py
    ```

## Team
*   This project was used by a team for the Capstone Project at the University of Wisconsin-Milwaukee.
*   AMI Team
    *   Member 1: YU-ERH, PAN
    *   Member 2: Yen-Lin, Chang
    *   Member 3: Carson K Lisowe
    *   Member 4: Taiwo Boluwaji Abe
    *   Member 5: Collin Brey
    *   Member 6: Matthew Scott Maijala

## Acknowledgements
Special thanks to the following open-source projects:
*   MCPO: https://github.com/open-webui/mcpo
*   MCP: https://github.com/modelcontextprotocol
*   Comitup: https://github.com/davesteele/comitup (Not directly related to this project, used for the network connection process on Raspberry Pi to send sensor data, and installed as a core component. We have not modified or disclosed any of its code. Due to its GPL-2.0 license, we hereby acknowledge it and express our thanks.)
