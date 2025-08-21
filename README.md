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

### Autodesk API Setup

1. Go to https://forge.autodesk.com/
2. Create a new app
3. Add the callback URL: `http://localhost:8080/api/auth/callback`
4. Copy the Client ID and Client Secret to your `.env` file

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

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the GitHub repository. 