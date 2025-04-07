<h1>FYP – aPatientDashboardForDataVisualization</h1>

<h2>🛠 Getting Started</h2>
<p>
  So you bravely spun up the Docker container—respect. But now the logs say it’s running on <code>http://0.0.0.0:8501</code> address.
</p>
<p>
  Here's the trick: 
  <strong><code>0.0.0.0</code></strong> means “I’m listening on everything” —not where you actually want to go, trust me if you try <strong><code>0.0.0.0:8501</code></strong> you'll get a page don't exist screen.
</p>
<p>
  To access the dashboard like a normal human, just open your browser and head to:
</p>
<p>
  <strong><code>http://localhost:8501</code></strong> <br>
  or if that fails, try <strong><code>127.0.0.1:8501</code></strong>—they’re basically twins.
</p>


<hr>

<h2>📖 About This Project</h2>
<p>
  This is my Final Year Project, where I, your humble and slightly overwhelmed developer, attempted to create a patient data dashboard using Streamlit.
</p>
<p>
  It's not groundbreaking software—it’s more like a <em>"It works, don’t touch it!"</em> kind of thing.
</p>
<p>
  There are two main forces holding this project together (barely):
</p>
<ul>
  <li>🌀 <strong>Chaos</strong> – lovingly cobbled together with vibes, caffeine, and whatever GenAI tools I could bribe into helping me.</li>
  <li>🌈 <strong>Hope</strong> – and maybe, just maybe, a few lines of working code that haven’t spontaneously combusted... yet.</li>
  <li>🛠️ <strong>Disclaimer:</strong> I mostly wrangled the backend and the connection code myself. Streamlit makes me feel like I did frontend too (don’t burst my bubble). As for Docker and the cursed database connection... I’m gonna need a wizard. Or therapy.</li>
</ul>


<hr>

<h2>🗂 Repo Layout (It's A Maze)</h2>
<p>If you thought this repo was clean and organized—ha! Think again. Let me walk you through it:</p>

<pre><code>
.
├── Admincredentials.py             # Admin credential management. erm... might be redundant now.
├── Dockerfile                      # Docker setup file.
├── Improved Test Data Injection.txt # My attempt at "improving" something... maybe?
├── api/
│   ├── schema.sql                  # Database schema file.
│   └── server.py                   # API server code.
├── arduino_code/
│   └── data_sender/                # ...currently home to one lonely file. (it's empty tho)
├── auth/
│   ├── jwt_auth.py                 # Stuff to authenticate you.
│   └── security.py                 # Not the safest, but it works. pls don't SQL inject him.
├── backend/
│   ├── Dockerfile
│   ├── app.py                      # Backend app functionality.
│   ├── models/                     # Contains some data models.
│   └── services/                   # Backend service logic.
├── database/
│   ├── init.sql                    # Initialization script (good luck running it).
│   └── temp_tables.sql             # Temporary database tables.
├── frontend/
│   ├── Dockerfile
│   └── static/
│       └── style.css               # The one and only CSS file. (It’s not great, don’t judge.)
├── pages/
│   ├── patient_dashboard.py        # Streamlit Patient Dashboard functionality.
│   └── admin/                      # Admin-specific pages.
├── static/
│   └── puppy_attack_doctor.png     # Totally relevant puppy image.
├── requirements.txt                # Python dependencies.
├── docker-compose.yml              # Docker config file.
└── ...and much, much more!
</code></pre>

<hr>

<h2>😅 Things I Didn’t Nail</h2>
<ul>
  <li><strong>CSS:</strong> Let’s just say I styled it <em>creatively</em>.</li>
  <li><strong>Security:</strong> Do <strong>NOT</strong>, under any circumstances, run this in production unless you're ready for chaos. (Shout out to those vibe coder bros that dared.)</li>
  <li><strong>Docker:</strong> Functional but clunky. The database connection might break your soul.</li>
  <li><strong>Empty Folders:</strong> Some folders exist purely to make me look busy.</li>
  <li><strong>Folder Names:</strong> Descriptive? No. Creative? Absolutely.</li>
</ul>

<hr>

<h2>🐾 Bonus Easter Egg</h2>
<p>Check out the <code>static/</code> folder for a totally relevant image that will definitely brighten your day.</p>
<p><em>Hint: It's called <code>puppy_attack_doctor.png</code>.</em></p>
<p>It’s not related to the project, but it brings joy to an otherwise serious FYP journey.</p>

<hr>

<h2>🧭 Final Notes</h2>
<p>
  This project is my journey through the perilous waters of coding, debugging, and barely surviving deadlines.
</p>
<p>
  If you’re here to fork, clone, or make sense of this mess—<strong>good luck, brave soul.</strong>
</p>
<p>
  And if you have suggestions or life hacks for dealing with Docker nightmares—I’m all ears.
</p>


<h2>💡 Proof That This Thing Actually Works (No, Seriously)</h2>
<p>
  Alright, so if you're like me and Docker decided to launch itself straight into the abyss, here's the janky-but-functional workaround I use to get things running:
</p>

<ol>
  <li>Open your terminal and run: <code>python websocket_server.py</code></li>
  <li>In another terminal (yes, you'll need two), run: <code>streamlit run main.py</code></li>
  <li>
    Streamlit will probably suggest something like <code>http://localhost:8501</code>, but—
    surprise! —sometimes that doesn't vibe with the database.
    When that happens, I just go straight to: <code>http://192.168.1.2:8501</code> (or whatever your LAN IP is).
  </li>
</ol>

<p>
  If everything went well, you should see a glorious, slightly chaotic dashboard. But—important note—make sure to initialize your SQL database first or you’ll be staring at a blank screen wondering what went wrong (spoiler: it’s always the database).
</p>

<p>
  That’s it. It <em>should</em> work. If it doesn’t… blame the stars, not the code. Good luck, and may the backend bugs stay forever hidden.
</p>
[p.s. remember to install the dependencies from requirement.txt, and also add the details in your .env file]

<p>  
  <h1>GOODBYE, I dont think I'll continue this project since my focus isn't really software dev anyway.... </h1>
</p>

