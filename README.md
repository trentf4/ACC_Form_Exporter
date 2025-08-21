# ACC Form Exporter

A Flask web application for exporting Autodesk Construction Cloud (ACC) forms as branded PDFs.

## Features

- **OAuth 2.0 Authentication**: Secure login with Autodesk Platform Services
- **Form Export**: Export individual forms or multiple forms as ZIP
- **Branded PDFs**: Add company logos and customize PDF appearance
- **Real-time Progress**: Live progress tracking during form processing
- **Settings Panel**: Configure logo, PDF options, and export preferences
- **Relationship Data**: Include form relationships and asset information

## Prerequisites for Beginners

### What You Need to Install

1. **Python** - The programming language this app uses
2. **Cursor** - A code editor to view and edit files
3. **Git** - To download the code from GitHub
4. **wkhtmltopdf** - To create PDF files

### Step 1: Install Python

1. **Download Python**
   - Go to https://www.python.org/downloads/
   - Click the big yellow "Download Python" button
   - Choose the latest version (like Python 3.11 or 3.12)

2. **Install Python**
   - Run the downloaded file (e.g., `python-3.12.0-amd64.exe`)
   - **IMPORTANT**: Check the box that says "Add Python to PATH"
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify Installation**
   - Press `Win + R` on your keyboard
   - Type `cmd` and press Enter
   - In the black window that opens, type: `python --version`
   - You should see something like "Python 3.12.0"

### Step 2: Install Cursor (Code Editor)

1. **Download Cursor**
   - Go to https://cursor.sh/
   - Click "Download for Windows"
   - Run the installer and follow the prompts

2. **Why Cursor?**
   - It's free and powerful
   - Has built-in AI assistance
   - Easy to use for beginners
   - Can help you understand and modify code

### Step 3: Install Git

1. **Download Git**
   - Go to https://git-scm.com/download/win
   - Click "Click here to download"
   - Run the installer

2. **Install Git**
   - Accept all default settings
   - Click "Next" through the installation
   - Click "Install"

## Quick Start (Step-by-Step for Beginners)

### Step 1: Download the Code

1. **Open Command Prompt**
   - Press `Win + R` on your keyboard
   - Type `cmd` and press Enter
   - A black window will open - this is your "terminal"

2. **Navigate to a Folder**
   - Type: `cd C:\Users\%USERNAME%\Desktop`
   - Press Enter
   - This takes you to your Desktop folder

3. **Download the Code**
   - Type: `git clone https://github.com/trentf4/ACC_Form_Exporter.git`
   - Press Enter
   - Wait for the download to complete
   - You should see a new folder called "ACC_Form_Exporter" on your Desktop

### Step 2: Open the Project in Cursor

1. **Open Cursor**
   - Find Cursor in your Start menu and click it
   - Or search for "Cursor" in Windows search

2. **Open the Project**
   - In Cursor, click "File" → "Open Folder"
   - Navigate to your Desktop
   - Click on the "ACC_Form_Exporter" folder
   - Click "Select Folder"

3. **What You'll See**
   - On the left side, you'll see all the files in the project
   - The main file is `app.py` - this is the application
   - `README.md` is this file you're reading
   - `requirements.txt` lists what needs to be installed

### Step 3: Install Required Software

1. **Install wkhtmltopdf (PDF Generator)**
   - Go to https://wkhtmltopdf.org/downloads.html
   - Click "Windows Installer" under "Stable Release"
   - Download and run the installer
   - Accept all defaults and install

2. **Install Python Packages**
   - In Cursor, press `Ctrl + `` (the key above Tab)
   - This opens the terminal inside Cursor
   - Type: `cd C:\Users\%USERNAME%\Desktop\ACC_Form_Exporter`
   - Press Enter
   - Type: `pip install -r requirements.txt`
   - Press Enter
   - Wait for installation to complete

### Step 4: Configure the Application

1. **Create Environment File**
   - In Cursor, right-click in the file explorer (left side)
   - Click "New File"
   - Name it `.env` (exactly like that, with the dot)

2. **Add Your Settings**
   - Open the `.env` file in Cursor
   - Copy and paste this content:
   ```
   FLASK_SECRET_KEY=your-secret-key-here
   AUTODESK_CLIENT_ID=your-client-id
   AUTODESK_CLIENT_SECRET=your-client-secret
   AUTODESK_CALLBACK_URL=http://localhost:8080/api/auth/callback
   PORT=8080
   ```

3. **Get Your Autodesk Credentials**
   - Follow the "Autodesk Platform Services Setup" section below
   - Replace `your-client-id` and `your-client-secret` with your actual values

### Step 5: Run the Application

1. **Start the App**
   - In the Cursor terminal (Ctrl + `)
   - Make sure you're in the right folder: `cd C:\Users\%USERNAME%\Desktop\ACC_Form_Exporter`
   - Type: `python app.py`
   - Press Enter

2. **What Should Happen**
   - You should see text like "Running on http://127.0.0.1:8080"
   - The app is now running!

3. **Access the Application**
   - Open your web browser (Chrome, Firefox, etc.)
   - Go to: `http://localhost:8080`
   - You should see the login page

### Step 6: Stop the Application

- To stop the app, go back to the Cursor terminal
- Press `Ctrl + C`
- The app will stop running

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```
FLASK_SECRET_KEY=your-secret-key-here
AUTODESK_CLIENT_ID=your-client-id
AUTODESK_CLIENT_SECRET=your-client-secret
AUTODESK_CALLBACK_URL=http://localhost:8080/api/auth/callback
PORT=8080
```

### Autodesk Platform Services Setup

#### Step 1: Create a New App

1. **Go to Autodesk Platform Services Console**
   - Visit https://forge.autodesk.com/
   - Sign in with your Autodesk account

2. **Create a New App**
   - Click **"Create App"** or **"New App"**
   - Choose **"Custom Integration"** as the app type
   - Give your app a name (e.g., "ACC Form Exporter")
   - Add a description (e.g., "Export ACC forms as branded PDFs")

#### Step 2: Configure App Settings

1. **Set Callback URL**
   - In your app settings, find the **"Callback URL"** field
   - For local development: `http://localhost:8080/api/auth/callback`
   - For production: `https://your-domain.com/api/auth/callback`

2. **Configure Scopes**
   - Add the following scopes to your app:
     - `data:read` - Read project and form data
     - `data:write` - Write form data (if needed)
     - `data:create` - Create new data (if needed)
     - `account:read` - Read account information

3. **Get Your Credentials**
   - Copy your **Client ID** and **Client Secret**
   - Add them to your `.env` file

#### Step 3: Configure ACC Permissions

1. **Access ACC Admin Panel**
   - Go to your ACC hub
   - Navigate to **Admin** → **Integrations**

2. **Add Custom Integration**
   - Click **"Add Integration"**
   - Select **"Custom Integration"**
   - Enter your app's Client ID from Autodesk Platform Services

#### Step 4: Test the Integration

1. **Verify Authentication**
   - Start your application: `python app.py`
   - Visit http://localhost:8080
   - Try logging in with your Autodesk account
   - You should be redirected to ACC for authorization

2. **Check Permissions**
   - After login, you should see your ACC hubs
   - Select a hub and verify you can see projects
   - Test form export functionality

### Production Deployment

#### Update Callback URL for Production

When deploying to production, update your app's callback URL:

1. **In Autodesk Platform Services Console**
   - Go to your app settings
   - Change callback URL to: `https://your-domain.com/api/auth/callback`

2. **In your `.env` file**
   - Update `AUTODESK_CALLBACK_URL` to match

3. **Update ACC Integration**
   - In ACC Admin → Integrations
   - Update the integration settings if needed

#### Security Considerations

- **HTTPS Required**: Production deployments must use HTTPS
- **Secret Management**: Store credentials securely (use environment variables)
- **Access Control**: Limit integration access to necessary projects only
- **Regular Review**: Periodically review and update permissions

## Usage

1. **Login**: Use your Autodesk account credentials
2. **Select Hub**: Choose the ACC hub containing your projects
3. **Configure Settings**: Upload your company logo and set PDF preferences
4. **Export Forms**: Select forms and export as individual PDFs or ZIP archive

## Requirements

- Python 3.7+
- Flask
- wkhtmltopdf (automatically detected in common installation paths)
- Autodesk Platform Services account
- ACC hub with appropriate permissions

## Environment Variables

The application uses the following environment variables (configured in `.env` file):

- `FLASK_SECRET_KEY`: Secret key for Flask sessions (required)
- `AUTODESK_CLIENT_ID`: Your Autodesk Platform Services Client ID (required)
- `AUTODESK_CLIENT_SECRET`: Your Autodesk Platform Services Client Secret (required)
- `AUTODESK_CALLBACK_URL`: OAuth callback URL (defaults to http://localhost:8080/api/auth/callback)
- `PORT`: Server port (defaults to 8080)
- `FLASK_DEBUG`: Enable debug mode (defaults to False, set to 'true' for development)

## Troubleshooting

### Common Issues

1. **"Not authenticated" errors**
   - Check your Client ID and Secret in `.env`
   - Verify callback URL matches exactly
   - Ensure app is properly configured in Autodesk Platform Services

2. **"No hubs found"**
   - Verify your ACC account has access to hubs
   - Check integration permissions in ACC Admin
   - Ensure the integration is assigned to projects

3. **"Forms not loading"**
   - Check ACC integration permissions for Forms access
   - Verify project has forms available
   - Check network connectivity to ACC APIs

4. **PDF generation fails**
   - Ensure wkhtmltopdf is installed and in PATH
   - Check file permissions for temporary files
   - Verify logo files are valid image formats

5. **"Python is not recognized"**
   - Reinstall Python and make sure to check "Add Python to PATH"
   - Restart your computer after installation
   - Try opening a new command prompt

6. **"pip is not recognized"**
   - This usually means Python isn't in your PATH
   - Reinstall Python with "Add Python to PATH" checked
   - Or try: `python -m pip install -r requirements.txt`

7. **"git is not recognized"**
   - Reinstall Git and make sure it's added to PATH
   - Restart your command prompt after installation

### Getting Help

- Check the application logs for detailed error messages
- Verify all environment variables are set correctly
- Test with a simple form export first
- Contact your ACC administrator for permission issues
- If you're stuck, try searching for the error message online

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the GitHub repository. 
