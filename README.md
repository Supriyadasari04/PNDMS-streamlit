
```markdown
# 🌐 Predictive Disaster Management System (PDNMS) – Streamlit Web App

A secure, responsive, and scalable web interface built with **Streamlit** and **SQLite**, allowing users to register, log in, and manage their profiles as part of a predictive disaster management system.

---

## 🧠 Features Implemented

✅ User Authentication  
✅ Secure Password Hashing (bcrypt)  
✅ Strong Password Validation  
✅ SQLite3 Database Integration  
✅ Session Management with Streamlit  
✅ User Profile Page (View & Update)  
✅ Responsive Streamlit UI with Tabs (Login & Sign Up)  
✅ Logout Functionality  

---

## 📁 Project Structure


PDNMS-Streamlit/
│
├── streamlit\_app.py         # Main Streamlit app
├── users.db                 # SQLite3 database (auto-created)
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── venv/                    # (Optional) Virtual environment folder




## 🔧 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/PDNMS-Streamlit.git
cd PDNMS-Streamlit
````

### 2. Create & Activate Virtual Environment (Optional but Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

<details>
<summary>📦 Example <code>requirements.txt</code></summary>

```
streamlit
bcrypt
```

</details>

---

## ▶️ Run the App

```bash
streamlit run streamlit_app.py
```

> App will automatically open in your browser at:
> [http://localhost:8501](http://localhost:8501)

---

## 🗄️ Database Schema

The `users.db` database has a single table:

### `users`

| Column     | Type | Description                   |
| ---------- | ---- | ----------------------------- |
| `username` | TEXT | Primary key, unique per user  |
| `password` | TEXT | Bcrypt-hashed password        |
| `email`    | TEXT | User email address (editable) |

---

## 🔐 Authentication Flow

### Sign Up

* Users enter `Username`, `Password`, `Email`
* Password is validated for:

  * At least 8 characters
  * One uppercase letter
  * One lowercase letter
  * One number
  * One special character
* If valid, the password is hashed using **bcrypt** and saved in the database

### Login

* Users enter `Username` and `Password`
* Entered password is verified using **bcrypt**

### Session Management

* After login, `st.session_state.authenticated` is set to `True`
* User is redirected to the home/profile page
* On logout, session state is cleared

---

## 👤 Profile Page Features

* View Current Username & Email
* Edit Username or Email
* Save changes → updates database and session state
* Logout button clears session and returns to login screen

---

## 🧪 Future Enhancements (Planned)

* 🔐 Admin & Role-based access
* 📈 Dashboard for disaster prediction visualization
* 📊 Integration of real-time disaster data APIs (USGS, NOAA, NASA)
* 📍 Interactive map view for global incidents
* 📨 Email verification and password reset
* 🔧 Dockerize the app for deployment
* ☁️ Host on Streamlit Cloud / Vercel

---

## 🤝 Contributing

Pull requests are welcome! Please fork the repo and open a PR with a meaningful description.

---

## 📜 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 🙋‍♀️ Author

**Supriya**
[GitHub](https://github.com/Supriyadasari04) | [LinkedIn](https://www.linkedin.com/in/supriyadasarii)

```
