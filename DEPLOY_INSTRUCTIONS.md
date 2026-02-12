# Deploying to Streamlit Cloud (Free)

Your project is now git-initialized and ready for deployment. Follow these steps:

## Step 1: Push to GitHub
1.  **Create a New Repository** on [GitHub](https://github.com/new).
    - name: e.g., `law-ai-app`
    - visibility: **Public** (for free Streamlit Cloud) or **Private** (if you have a pro account, but public is easiest).
    - **Do NOT** initialize with README, .gitignore, or License (we have local ones).

2.  **Push your code**:
    Open your terminal in `d:\PhythonProject\LawProject` and run:
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/law-ai-app.git
    git branch -M main
    git push -u origin main
    ```

## Step 2: Deploy on Streamlit Cloud
1.  Go to [share.streamlit.io](https://share.streamlit.io/).
2.  Log in with GitHub.
3.  Click **"New app"**.
4.  Select your repository (`law-ai-app`) and branch (`main`).
5.  **Main file path**: `app_streamlit.py`
6.  Click **"Deploy!"**.

## Step 3: Configure Secrets (Critical)
The app needs your OpenAI API Key to work.
1.  On your Streamlit App dashboard, click the **Settings** (three dots) -> **Settings**.
2.  Go to **"Secrets"**.
3.  Paste the following content (from your local `.env`):
    ```toml
    OPENAI_API_KEY = "sk-..."
    ```
4.  Save. The app should restart and work!

## Note on Database
This repository includes a pre-built chroma database in `data/chroma`. It is small enough (~5MB) to host on GitHub for this demo.
For a production app, you would typically generate this during build or host it externally.
