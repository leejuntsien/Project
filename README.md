FYP-aPatientDashboardForDataVisualization
Getting Started
Access the dashboard like this:


About This Project
This is my Final Year Project, where I, your humble and slightly overwhelmed developer, attempted to create a patient data dashboard using Streamlit. It's not groundbreaking software—it’s more like a "It works, don't touch it!" kind of thing.
There are two main parts holding this project together:


Repo Layout (It's A Maze)
If you thought this repo was clean and organized, ha—think again. Let me walk you through it:
.
├── Admincredentials.py          # Admin credential management. erm... now i look at it, it might be    redundant
├── Dockerfile                   # Docker setup file.
├── Improved Test Data Injection.txt # My attempt at "improving" something...? (p.s. sometimes when you have working code and you want to compare just save them as txt file, ...maybe)
├── api/
│   ├── schema.sql               # Database schema file.
│   └── server.py                # API server code.
├── arduino_code/                # ...currently home to one lonely file. (it is empty tho)
│   └── data_sender/
├── auth/                        # Stuff to authenticate you (not the safest, but it works, pls dont sql inject him).
│   ├── jwt_auth.py
│   └── security.py
├── backend/                     # The backend brain. actually not really there is still a lot more mess where i forgot to clean the code
│   ├── Dockerfile
│   ├── app.py                   # Backend app functionality.
│   ├── models/                  # Contains some data models.
│   └── services/                # Services for the backend.
├── database/                    # SQL scripts, temporary tables, and my database manager.
│   ├── init.sql                 # Initialization script (good luck running it).
│   └── temp_tables.sql          # Temporary database tables.
├── frontend/                    # CSS and frontend static files.
│   ├── Dockerfile
│   └── static/
│       └── style.css            # The one and only style file (it’s not great, don’t judge).
├── pages/                       # Streamlit page logic.
│   ├── patient_dashboard.py     # Example: Patient Dashboard functionality.
│   └── admin/                   # Admin-specific pages and logic.
├── static/                      # Random static assets.
│   └── puppy_attack_doctor.png  # Totally relevant puppy image.
├── requirements.txt             # Python dependencies.
├── docker-compose.yml           # Docker configuration.
└── ...and much, much more!


Things I Didn't Nail
-CSS: Let's just say I styled it "creatively."
-Security: Do NOT, under any circumstances, run this in production unless you're ready for chaos. (Shout out to those vibe coder bros that dared)
-Docker: It’s functional but clunky. Also, the database connection might break your soul.
-Empty Folders: Some folders exist purely to fill space and make me look busy.
-Folder Names: Descriptive? No. Creative? Yes!


Bonus Easter Egg 🐾
Check out  if you need a laugh. It’s not related to the project, but it brings joy to an otherwise serious FYP journey.

Final Notes
This project is my journey through the perilous waters of coding, debugging, and barely surviving deadlines. If you’re here to fork, clone, or make sense of this mess—good luck, brave soul. And if you have suggestions or life hacks for dealing with Docker nightmares, I’m all ears.