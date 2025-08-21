# ACC Form Exporter

A Flask web application for exporting Autodesk Construction Cloud (ACC) forms as branded PDFs.

## Features

- **OAuth 2.0 Authentication**: Secure login with Autodesk Platform Services
- **Form Export**: Export individual forms or multiple forms as ZIP
- **Branded PDFs**: Add company logos and customize PDF appearance
- **Real-time Progress**: Live progress tracking during form processing
- **Settings Panel**: Configure logo, PDF options, and export preferences
- **Relationship Data**: Include form relationships and asset information

## Quick Start

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/ACC_Form_Exporter.git
   cd ACC_Form_Exporter
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Install wkhtmltopdf**
   - Windows: Download from https://wkhtmltopdf.org/downloads.html
   - macOS: `brew install wkhtmltopdf`
   - Linux: `sudo apt-get install wkhtmltopdf`

4. **Configure environment**
   - Copy `env_template.txt` to `.env`
   - Fill in your Autodesk API credentials

5. **Run the application**
   ```
   python app.py
   ```

6. **Access the application**
   - Open http://localhost:8080 in your browser
   - Login with your Autodesk account

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
- wkhtmltopdf
- Autodesk Platform Services account
- ACC hub with appropriate permissions

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

### Getting Help

- Check the application logs for detailed error messages
- Verify all environment variables are set correctly
- Test with a simple form export first
- Contact your ACC administrator for permission issues

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the GitHub repository. 
