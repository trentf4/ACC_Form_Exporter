"""
ACC Form Tool - Autodesk Construction Cloud Form Export Application
==================================================================

Purpose:
    This tool is designed to export Autodesk Construction Cloud (ACC) forms 
    with customizable naming conventions. It provides a professional web interface 
    for downloading completed forms as PDFs with custom branding and advanced 
    export capabilities.

Key Features:
    - Smart Naming: Auto-suggest filenames from form reference numbers and data
    - Custom Branding: Add company logos to exported PDFs
    - Bulk Export: Export multiple forms simultaneously with individual naming
    - Professional Interface: Modern, responsive design for construction industry use
    - Secure Authentication: OAuth 2.0 integration with Autodesk Platform Services

Development Details:
    - Developer: Trent Field
    - Organization: ARKANCE ANZ
    - Created: August 2025
    - Technology: Python Flask, Azure App Service, Autodesk Platform Services

Contact:
    For support, questions, or feature requests, please contact:
    - Developer: Trent Field
    - Organization: ARKANCE ANZ

License:
    This project is licensed under the MIT License.

Built with ❤️ for the construction industry
Developed by Trent Field of ARKANCE ANZ - August 2025
"""

from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify, Response, make_response, flash
import os
from dotenv import load_dotenv
import tempfile
from authlib.integrations.flask_client import OAuth
import requests
from urllib.parse import urljoin, urlparse
import io
import zipfile
import pdfkit
import time
import random
import string
import json
import re
import sqlite3
from datetime import datetime, timedelta

# Application Metadata
__version__ = "1.2.0"
__author__ = "Trent Field"
__organization__ = "ARKANCE ANZ"
__created__ = "August 2025"

# Load environment variables
load_dotenv()

# Set default values for environment variables (can be overridden by .env file)
if not os.getenv('PORT'):
    os.environ['PORT'] = '8080'
if not os.getenv('AUTODESK_CALLBACK_URL'):
    os.environ['AUTODESK_CALLBACK_URL'] = 'http://localhost:8080/api/auth/callback'

# Verify required environment variables
required_env_vars = ['AUTODESK_CLIENT_ID', 'AUTODESK_CLIENT_SECRET']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Debug: Print environment variables
print("Environment Variables:")
print(f"FLASK_SECRET_KEY: {os.environ.get('FLASK_SECRET_KEY')}")
print(f"AUTODESK_CLIENT_ID: {os.environ.get('AUTODESK_CLIENT_ID')}")
print(f"AUTODESK_CALLBACK_URL: {os.environ.get('AUTODESK_CALLBACK_URL')}")
print(f"PORT: {os.environ.get('PORT')}")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")  # Change this in production

# Configure OAuth for Autodesk
oauth = OAuth(app)
autodesk = oauth.register(
    name='autodesk',
    client_id=os.environ.get("AUTODESK_CLIENT_ID"),
    client_secret=os.environ.get("AUTODESK_CLIENT_SECRET"),
    access_token_url='https://developer.api.autodesk.com/authentication/v2/token',
    authorize_url='https://developer.api.autodesk.com/authentication/v2/authorize',
    client_kwargs={
        'scope': 'data:read data:write data:create account:read',
        'token_endpoint_auth_method': 'client_secret_post'
    }
)

# Configure pdfkit with wkhtmltopdf path
# Try to find wkhtmltopdf in common installation paths
def find_wkhtmltopdf():
    possible_paths = [
        'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        '/usr/local/bin/wkhtmltopdf',
        '/usr/bin/wkhtmltopdf',
        'wkhtmltopdf'  # Try system PATH
    ]
    
    for path in possible_paths:
        if os.path.exists(path) or path == 'wkhtmltopdf':
            return path
    
    # If not found, return the default Windows path
    return 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'

config = pdfkit.configuration(wkhtmltopdf=find_wkhtmltopdf())

def get_autodesk_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

def is_authenticated():
    token = session.get('access_token')
    expires_at = session.get('token_expires_at')
    return token and (not expires_at or expires_at > time.time())

@app.route('/')
def index():
    if not is_authenticated():
        session.clear()
        return redirect(url_for('login'))
    return redirect(url_for('select_hub'))

@app.route('/select_hub')
def select_hub():
    print("Session access_token in /select_hub:", session.get('access_token'))
    if 'access_token' not in session:
        return redirect(url_for('index'))
    
    headers = {
        'Authorization': f'Bearer {session["access_token"]}',
        'Content-Type': 'application/json'
    }
    try:
        print(f"Making API call to fetch hubs with token: {session['access_token'][:20]}...")
        response = requests.get('https://developer.api.autodesk.com/project/v1/hubs', headers=headers)
        print(f"API response status: {response.status_code}")
        response.raise_for_status()
        hubs_data = response.json()
        print(f"Raw hubs response: {hubs_data}")
        
        # Filter for ACC hubs only
        acc_hubs = []
        all_hubs = hubs_data.get('data', [])
        print(f"Total hubs found: {len(all_hubs)}")
        
        for hub in all_hubs:
            ext_type = hub['attributes']['extension'].get('type', '')
            print(f"Hub '{hub['attributes']['name']}' has extension type: {ext_type}")
            if ext_type == 'hubs:autodesk.core:Hub':
                acc_hubs.append({
                    'id': hub['id'],
                    'name': hub['attributes']['name'],
                    'description': hub['attributes'].get('description', ''),
                    'region': hub['attributes'].get('region', 'US'),
                    'type': 'ACC'
                })
        
        print(f"ACC hubs found: {len(acc_hubs)}")
        if not acc_hubs:
            # If no ACC hubs found, try to show all hubs as a fallback
            print("No ACC hubs found, showing all available hubs...")
            all_hubs_formatted = []
            for hub in all_hubs:
                ext_type = hub['attributes']['extension'].get('type', '')
                # Map extension types to display names
                if 'bim360' in ext_type.lower():
                    display_type = 'BIM 360'
                elif 'autodesk.core' in ext_type.lower():
                    display_type = 'ACC'
                else:
                    display_type = ext_type
                
                all_hubs_formatted.append({
                    'id': hub['id'],
                    'name': hub['attributes']['name'],
                    'description': hub['attributes'].get('description', ''),
                    'region': hub['attributes'].get('region', 'US'),
                    'type': display_type
                })
            
            if all_hubs_formatted:
                print(f"Showing {len(all_hubs_formatted)} total hubs as fallback")
                # Organize hubs by region
                hubs_by_region = {}
                for hub in all_hubs_formatted:
                    region = hub['region']
                    if region not in hubs_by_region:
                        hubs_by_region[region] = []
                    hubs_by_region[region].append(hub)
                response = make_response(render_template('hub_selector.html', hubs_by_region=hubs_by_region))
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            else:
                # Clear session if no hubs found at all
                session.clear()
                flash('No hubs found. Please make sure you have access to Autodesk Construction Cloud and log in again.', 'warning')
                return redirect(url_for('index'))
        
        print(f"Found {len(acc_hubs)} ACC hubs.")
        # Organize ACC hubs by region
        hubs_by_region = {}
        for hub in acc_hubs:
            region = hub['region']
            if region not in hubs_by_region:
                hubs_by_region[region] = []
            hubs_by_region[region].append(hub)
        response = make_response(render_template('hub_selector.html', hubs_by_region=hubs_by_region))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error fetching hubs: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        # Clear session if API call fails (token might be invalid)
        session.clear()
        flash(f'Error fetching hubs: {str(e)}. Please log in again.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        # Clear session if unexpected error occurs
        session.clear()
        flash(f'Unexpected error: {str(e)}. Please log in again.', 'error')
        return redirect(url_for('index'))

@app.route('/form_downloader')
def form_downloader():
    if 'access_token' not in session:
        return redirect(url_for('index'))
    
    hub_id = request.args.get('hub_id')
    if not hub_id:
        return redirect(url_for('select_hub'))
    
    # Store the selected hub_id in the session
    session['selected_hub_id'] = hub_id
    
    # Get projects for the selected hub
    headers = {
        'Authorization': f'Bearer {session["access_token"]}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get hub details to extract region and name
        hub_response = requests.get(
            f'https://developer.api.autodesk.com/project/v1/hubs/{hub_id}',
            headers=headers
        )
        hub_response.raise_for_status()
        hub_data = hub_response.json()
        hub_region = hub_data['data']['attributes'].get('region', 'US')
        hub_name = hub_data['data']['attributes'].get('name', 'Unknown Hub')
        
        # Get projects for the hub
        response = requests.get(
            f'https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects',
            headers=headers
        )
        response.raise_for_status()
        projects_data = response.json()
        
        # Format project data for template
        projects = []
        for project in projects_data.get('data', []):
            project_info = {
                'id': project['id'],
                'name': project['attributes']['name'],
                'description': project['attributes'].get('description', '')
            }
            projects.append(project_info)
        
        return render_template('form_downloader.html', projects=projects, hub_region=hub_region, hub_name=hub_name)
    except Exception as e:
        print(f"Error fetching projects: {str(e)}")
        flash(f'Error fetching projects: {str(e)}', 'error')
        return redirect(url_for('select_hub'))

@app.route('/login')
def login():
    # Verify environment variables are set
    client_id = os.getenv('AUTODESK_CLIENT_ID')
    callback_url = os.getenv('AUTODESK_CALLBACK_URL')
    
    if not client_id or not callback_url:
        print("Error: Missing required environment variables")
        return "Error: Missing required environment variables. Please check your .env file.", 500
    
    # Generate a random state value
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    session['oauth_state'] = state
    
    # Construct the authorization URL for Autodesk ID with correct scopes for ACC
    auth_url = (
        'https://developer.api.autodesk.com/authentication/v2/authorize'
        f'?response_type=code'
        f'&client_id={client_id}'
        f'&redirect_uri={callback_url}'
        f'&scope=data:read data:write data:create account:read'
        f'&state={state}'
    )
    
    print(f"Generated auth URL: {auth_url}")
    print(f"Client ID: {client_id}")
    print(f"Callback URL: {callback_url}")
    print(f"State: {state}")
    return render_template('login.html', auth_url=auth_url)

@app.route('/api/auth/callback')
def oauth_callback():
    try:
        # Get the authorization code from the callback
        code = request.args.get('code')
        if not code:
            return redirect(url_for('index'))
        
        # Exchange the code for a token
        token_url = 'https://developer.api.autodesk.com/authentication/v2/token'
        token_data = {
            'client_id': os.getenv('AUTODESK_CLIENT_ID'),
            'client_secret': os.getenv('AUTODESK_CLIENT_SECRET'),
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': os.getenv('AUTODESK_CALLBACK_URL')
        }
        
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()
        token = response.json()
        
        # Store the token in session
        session['access_token'] = token['access_token']
        print("Token set in session (callback):", session.get('access_token'))
        session['refresh_token'] = token.get('refresh_token')
        session['token_expires_at'] = time.time() + token['expires_in']
        
        # Clear the callback URL from session
        session.pop('oauth_callback', None)
        
        print("Authentication successful, redirecting to hub selector...")
        return redirect(url_for('select_hub'))
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/search_projects', methods=['GET'])
def search_projects():
    print("🔍 Search projects endpoint called")
    if 'access_token' not in session:
        print("❌ No access token in session")
        return jsonify({'error': 'Not authenticated'}), 401
    
    search_query = request.args.get('query', '')
    print(f"🔍 Search query: '{search_query}'")
    
    try:
        # Get projects from ACC - use the selected hub if available
        headers = get_autodesk_headers(session['access_token'])
        
        # Check if we have a selected hub in session
        selected_hub_id = session.get('selected_hub_id')
        
        if selected_hub_id:
            print(f"🔍 Using selected hub: {selected_hub_id}")
            # Search projects in the selected hub only
            projects_response = requests.get(
                f'https://developer.api.autodesk.com/project/v1/hubs/{selected_hub_id}/projects',
                headers=headers
            )
            projects_response.raise_for_status()
            projects_data = projects_response.json()
            
            all_projects = []
            for project in projects_data.get('data', []):
                project_name = project['attributes']['name'].lower()
                project_desc = project['attributes'].get('description', '').lower()
                
                # If no search query, return all projects, otherwise filter
                if (not search_query or 
                    search_query.lower() in project_name or 
                    search_query.lower() in project_desc):
                    project_info = {
                        'id': project['id'],
                        'name': project['attributes']['name'],
                        'description': project['attributes'].get('description', '')
                    }
                    all_projects.append(project_info)
                    print(f"✅ Found project: {project_info['name']}")
            
            print(f"🔍 Returning {len(all_projects)} projects from selected hub")
            return jsonify({'projects': all_projects})
        else:
            print("🔍 No selected hub, fetching all hubs...")
            # Fallback: get all hubs and projects (original behavior)
            try:
                hubs_response = requests.get('https://developer.api.autodesk.com/project/v1/hubs', headers=headers)
                hubs_response.raise_for_status()
                hubs_data = hubs_response.json()
                print(f"🔍 Found {len(hubs_data.get('data', []))} hubs")
                
                # Search through projects in each hub
                all_projects = []
                for hub in hubs_data.get('data', []):
                    hub_id = hub['id']
                    hub_name = hub['attributes']['name']
                    print(f"🔍 Checking hub: {hub_name}")
                    
                    try:
                        projects_response = requests.get(
                            f'https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects',
                            headers=headers
                        )
                        projects_response.raise_for_status()
                        projects_data = projects_response.json()
                        
                        # Filter projects based on search query
                        for project in projects_data.get('data', []):
                            project_name = project['attributes']['name'].lower()
                            project_desc = project['attributes'].get('description', '').lower()
                            
                            # Check if search query matches project name or description
                            if (search_query.lower() in project_name or 
                                search_query.lower() in project_desc):
                                project_info = {
                                    'id': project['id'],
                                    'name': project['attributes']['name'],
                                    'description': project['attributes'].get('description', '')
                                }
                                all_projects.append(project_info)
                                print(f"✅ Found matching project: {project_info['name']}")
                    except Exception as hub_error:
                        print(f"⚠️ Error fetching projects from hub {hub_name}: {hub_error}")
                        continue
                
                print(f"🔍 Returning {len(all_projects)} projects")
                return jsonify({'projects': all_projects})
            except Exception as e:
                print(f"❌ Error fetching hubs: {e}")
                return jsonify({'error': f'Failed to fetch hubs: {str(e)}'}), 500
            
    except Exception as e:
        print(f"❌ Error searching projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_project_forms', methods=['GET'])
def get_project_forms():
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': 'No project ID provided'}), 400
    
    try:
        # Get forms for the project using the ACC API
        headers = get_autodesk_headers(session['access_token'])
        
        # Remove the "b." prefix from the project ID if it exists
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        
        # First get form templates
        templates_response = requests.get(
            f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/form-templates',
            headers=headers
        )
        templates_response.raise_for_status()
        templates_data = templates_response.json()
        
        # Get forms for each template
        all_forms = []
        for template in templates_data.get('data', []):
            template_id = template['id']
            template_name = template.get('name', 'Unnamed Template')
            
            # Get forms for this template
            forms_response = requests.get(
                f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms',
                headers=headers,
                params={'templateId': template_id}
            )
            forms_response.raise_for_status()
            forms_data = forms_response.json()
            
            # Format the forms data for the frontend
            for form in forms_data.get('data', []):
                # Get form with relationships
                form_with_relationships = get_form_with_relationships(form, acc_project_id, headers)
                
                all_forms.append({
                    'id': form['id'],
                    'name': form.get('name', template_name),
                    'status': form.get('status', 'Unknown'),
                    'form_date': form.get('formDate', ''),
                    'updated_at': form.get('updatedAt', ''),
                    'description': form.get('description', ''),
                    'notes': form.get('notes', ''),
                    'created_by': form.get('createdBy', ''),
                    'template_name': template_name,
                    'pdf_url': form.get('pdfUrl', ''),
                    'pdf_values': form.get('pdfValues', []),
                    'tabular_values': form.get('tabularValues', {}),
                    'custom_values': form.get('customValues', []),
                    'related_assets': form_with_relationships.get('related_assets', []),
                    'asset_count': form_with_relationships.get('asset_count', 0)
                })
        
        return jsonify({'forms': all_forms})
    except Exception as e:
        print(f"Error fetching forms: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_form', methods=['POST'])
def download_form():
    if 'access_token' not in session:
        return redirect(url_for('index'))
    
    temp_file_path = None
    try:
        form_id = request.form.get('form_id')
        project_id = request.form.get('project_id')
        
        if not form_id or not project_id:
            return "Missing form_id or project_id", 400
        
        # Remove the "b." prefix from the project ID if it exists
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        
        # First get the form details to verify it exists and get the PDF URL
        headers = get_autodesk_headers(session['access_token'])
        form_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms/{form_id}'
        print(f"Getting form details from: {form_url}")
        
        form_response = requests.get(form_url, headers=headers)
        form_response.raise_for_status()
        form_data = form_response.json()
        
        if not form_data.get('data', {}).get('pdfUrl'):
            return "Form PDF not available", 404
        
        # Download the PDF
        pdf_url = form_data['data']['pdfUrl']
        pdf_response = requests.get(pdf_url, headers=headers)
        pdf_response.raise_for_status()
        
        # Save to temporary file
        temp_file_path = os.path.join(tempfile.gettempdir(), f'form_{form_id}.pdf')
        with open(temp_file_path, 'wb') as f:
            f.write(pdf_response.content)
        
        # Send the file
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=f'form_{form_id}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error downloading form: {str(e)}")
        return str(e), 500
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/view_form', methods=['GET'])
def view_form():
    if 'access_token' not in session:
        return redirect(url_for('index'))
    try:
        form_id = request.args.get('form_id')
        project_id = request.args.get('project_id')
        
        if not form_id or not project_id:
            return "Missing form_id or project_id", 400
        
        # Remove the "b." prefix from the project ID if it exists
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        print(f"Using ACC Project ID: {acc_project_id}")
        headers = get_autodesk_headers(session['access_token'])
        
        # For now, skip project details and use default values
        project_name = "Project"
        project_logo_url = None
        print(f"Using default project name: {project_name}")
        
        # Get form details from the forms list
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms'
        print(f"Getting forms list from: {forms_url}")
        forms_response = requests.get(forms_url, headers=headers)
        print(f"Forms response status: {forms_response.status_code}")
        if not forms_response.ok:
            print(f"Forms response error: {forms_response.text}")
            return f"Error getting forms: {forms_response.status_code} - {forms_response.text}", 500
        forms_response.raise_for_status()
        forms_data = forms_response.json()
        print(f"Forms data received, looking for form ID: {form_id}")
        
        # Find the specific form in the list
        form_data = None
        for form in forms_data.get('data', []):
            if form['id'] == form_id:
                form_data = form
                print(f"Found form: {form_data}")
                break
        
        if not form_data:
            return f"Form with ID {form_id} not found", 404
        
        # Prepare form info for template
        form_info = {
            'name': form_data.get('name', 'Unnamed Form'),
            'sections': []  # Will be populated from pdf_values, tabular_values, and custom_values
        }
        
        # Process form data
        id_mapping = {}
        if form_data.get('formTemplate') and form_data['formTemplate'].get('id_mapping'):
            id_mapping = form_data['formTemplate']['id_mapping']
        elif form_data.get('form_template') and form_data['form_template'].get('id_mapping'):
            id_mapping = form_data['form_template']['id_mapping']
        
        def get_label(item_id, fallback):
            return id_mapping.get(item_id, fallback)
        
        # Process all form values
        section_map = {}
        
        # Process pdf_values
        for item in form_data.get('pdfValues', []):
            section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'General'))
            if section_title not in section_map:
                section_map[section_title] = []
            
            if item.get('dateVal'):
                ftype, fval = 'date', item['dateVal']
            elif item.get('numVal') is not None:
                ftype, fval = 'number', item['numVal']
            elif item.get('boolVal') is not None:
                ftype, fval = 'bool', item['boolVal']
            elif item.get('listVal'):
                ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
            elif item.get('objVal'):
                ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
            elif item.get('textVal'):
                ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
            else:
                ftype, fval = 'text', ''
            
            section_map[section_title].append({
                'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                'type': ftype,
                'value': fval
            })
        
        # Process tabular_values
        for section, rows in form_data.get('tabularValues', {}).items():
            section_title = get_label(section, section)
            fields = []
            if rows:
                for idx, row in enumerate(rows, 1):
                    for key, value in row.items():
                        label = get_label(key, key)
                        if isinstance(value, bool):
                            ftype = 'bool'
                        elif isinstance(value, (int, float)):
                            ftype = 'number'
                        elif isinstance(value, list):
                            ftype = 'list'
                            value = [get_label(v, v) for v in value]
                        elif isinstance(value, dict):
                            ftype = 'object'
                            value = {get_label(k, k): get_label(v, v) for k, v in value.items()}
                        else:
                            ftype = 'text'
                            value = get_label(value, value)
                        fields.append({
                            'label': f"{label} (Row {idx})",
                            'type': ftype,
                            'value': value
                        })
            if fields:
                section_map[section_title] = section_map.get(section_title, []) + fields
        
        # Process custom_values
        for item in form_data.get('customValues', []):
            section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'Custom Fields'))
            if section_title not in section_map:
                section_map[section_title] = []
            
            if item.get('dateVal'):
                ftype, fval = 'date', item['dateVal']
            elif item.get('numVal') is not None:
                ftype, fval = 'number', item['numVal']
            elif item.get('boolVal') is not None:
                ftype, fval = 'bool', item['boolVal']
            elif item.get('listVal'):
                ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
            elif item.get('objVal'):
                ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
            elif item.get('textVal'):
                ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
            else:
                ftype, fval = 'text', ''
            
            section_map[section_title].append({
                'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                'type': ftype,
                'value': fval
            })
        
        # Convert section map to list of sections
        form_info['sections'] = [{'title': title, 'fields': fields} for title, fields in section_map.items()]
        print(f"Final form info: {form_info}")
        print(f"Number of sections: {len(form_info['sections'])}")
        for i, section in enumerate(form_info['sections']):
            print(f"Section {i+1}: {section['title']} with {len(section['fields'])} fields")
        
        # Check if JSON response is requested
        if request.args.get('json') == 'true':
            form_info['project_name'] = project_name
            return jsonify(form_info)
        
        return render_template('view_form.html', 
                             form=form_info, 
                             project_id=project_id,
                             project_name=project_name,
                             project_logo_url=project_logo_url)
    except Exception as e:
        print(f"Error viewing form: {str(e)}")
        return str(e), 500

@app.route('/get_project_logo')
def get_project_logo():
    if 'access_token' not in session:
        return "Not authenticated", 401
    
    logo_url = request.args.get('logo_url')
    if not logo_url:
        return "Missing logo URL", 400
    headers = get_autodesk_headers(session['access_token'])
    r = requests.get(logo_url, headers=headers)
    if r.status_code != 200:
        return "Error fetching logo", r.status_code
    return Response(r.content, mimetype=r.headers['Content-Type'])

@app.route('/export_forms')
def export_forms():
    if 'access_token' not in session:
        return redirect(url_for('index'))
    
    form_ids = request.args.get('form_ids', '')
    export_type = request.args.get('type', 'zip')
    project_id = request.args.get('project_id')
    
    if not form_ids or not project_id:
        return abort(400, 'Missing form_ids or project_id')
    
    form_ids = form_ids.split(',')
    # Get project details (for logo, name)
    headers = get_autodesk_headers(session['access_token'])
    acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
    project_response = requests.get(
        f'https://developer.api.autodesk.com/project/v1/hubs/{session["selected_hub_id"]}/projects/{acc_project_id}',
        headers=headers
    )
    project_response.raise_for_status()
    project_data = project_response.json()
    project_name = project_data['data']['attributes']['name']
    project_logo_url = project_data['data']['attributes'].get('logoUrl')
    
    # Fetch forms data from the API
    url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms'
    forms_response = requests.get(url, headers=headers)
    if not forms_response.ok:
        return f"Error fetching forms: {forms_response.status_code} - {forms_response.text}", forms_response.status_code
    
    forms_data = forms_response.json()
    if not isinstance(forms_data, dict) or 'data' not in forms_data:
        return "Invalid forms data response", 500
    
    # For each form, generate PDF
    pdf_files = []
    def extract_reference_number(sections):
        for section in sections:
            for field in section['fields']:
                if 'reference number' in field['label'].lower() and field['value']:
                    # If value is a list or dict, join or stringify
                    if isinstance(field['value'], list):
                        return '_'.join(str(v) for v in field['value'])
                    elif isinstance(field['value'], dict):
                        return '_'.join(f"{k}-{v}" for k, v in field['value'].items())
                    else:
                        return str(field['value'])
        return None
    for form_id in form_ids:
        form_data = None
        for form in forms_data.get('data', []):
            if form['id'] == form_id:
                form_data = form
                break
        if not form_data:
            continue
        # Prepare id mapping and sections (reuse logic from /view_form)
        id_mapping = {}
        if form_data.get('formTemplate') and form_data['formTemplate'].get('id_mapping'):
            id_mapping = form_data['formTemplate']['id_mapping']
        elif form_data.get('form_template') and form_data['form_template'].get('id_mapping'):
            id_mapping = form_data['form_template']['id_mapping']
        def get_label(item_id, fallback):
            return id_mapping.get(item_id, fallback)
        sections = []
        pdf_values = form_data.get('pdfValues', [])
        section_map = {}
        for item in pdf_values:
            section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'General'))
            if section_title not in section_map:
                section_map[section_title] = []
            if item.get('dateVal'):
                ftype, fval = 'date', item['dateVal']
            elif item.get('numVal') is not None:
                ftype, fval = 'number', item['numVal']
            elif item.get('boolVal') is not None:
                ftype, fval = 'bool', item['boolVal']
            elif item.get('listVal'):
                ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
            elif item.get('objVal'):
                ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
            elif item.get('textVal'):
                ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
            else:
                ftype, fval = 'text', ''
            section_map[section_title].append({
                'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                'type': ftype,
                'value': fval
            })
        tabular_values = form_data.get('tabularValues', {})
        for section, rows in tabular_values.items():
            section_title = get_label(section, section)
            fields = []
            if rows:
                for idx, row in enumerate(rows, 1):
                    for key, value in row.items():
                        label = get_label(key, key)
                        if isinstance(value, bool):
                            ftype = 'bool'
                        elif isinstance(value, (int, float)):
                            ftype = 'number'
                        elif isinstance(value, list):
                            ftype = 'list'
                            value = [get_label(v, v) for v in value]
                        elif isinstance(value, dict):
                            ftype = 'object'
                            value = {get_label(k, k): get_label(v, v) for k, v in value.items()}
                        else:
                            ftype = 'text'
                            value = get_label(value, value)
                        fields.append({
                            'label': f"{label} (Row {idx})",
                            'type': ftype,
                            'value': value
                        })
            if fields:
                section_map[section_title] = section_map.get(section_title, []) + fields
        custom_values = form_data.get('customValues', [])
        for item in custom_values:
            section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'Custom Fields'))
            if section_title not in section_map:
                section_map[section_title] = []
            if item.get('dateVal'):
                ftype, fval = 'date', item['dateVal']
            elif item.get('numVal') is not None:
                ftype, fval = 'number', item['numVal']
            elif item.get('boolVal') is not None:
                ftype, fval = 'bool', item['boolVal']
            elif item.get('listVal'):
                ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
            elif item.get('objVal'):
                ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
            elif item.get('textVal'):
                ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
            else:
                ftype, fval = 'text', ''
            section_map[section_title].append({
                'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                'type': ftype,
                'value': fval
            })
        # Convert section map to list of sections
        sections = [{'title': title, 'fields': fields} for title, fields in section_map.items()]
        # Prepare form info for template
        form_info = {
            'name': form_data.get('name', 'Unnamed Form'),
            'sections': sections
        }
        # Render HTML for PDF (hide export/back buttons)
        html = render_template('view_form.html', form=form_info, project_id=project_id, project_name=project_name, project_logo_url=project_logo_url, hide_export_buttons=True)
        pdf_io = io.BytesIO()
        pdf_bytes = pdfkit.from_string(html, output_path=False, configuration=config)
        pdf_io.write(pdf_bytes)
        pdf_io.seek(0)
        # Use reference number for file name if available
        ref_number = extract_reference_number(sections)
        if ref_number:
            safe_name = str(ref_number).replace(' ', '_').replace('/', '_') + '.pdf'
        else:
            safe_name = form_info['name'].replace(' ', '_').replace('/', '_') + '.pdf'
        pdf_files.append((safe_name, pdf_io.read()))
    # Return ZIP or merged PDF
    if export_type == 'merged':
        # Merge PDFs (simple concat, not true PDF merge, but works for most viewers)
        merged_io = io.BytesIO()
        for _, pdf_bytes in pdf_files:
            merged_io.write(pdf_bytes)
        merged_io.seek(0)
        return send_file(merged_io, as_attachment=True, download_name='merged_forms.pdf', mimetype='application/pdf')
    else:
        # ZIP
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w') as zf:
            for name, pdf_bytes in pdf_files:
                zf.writestr(name, pdf_bytes)
        zip_io.seek(0)
        return send_file(zip_io, as_attachment=True, download_name='forms.zip', mimetype='application/zip')

def get_form_asset_relationships(form_data, project_id, headers):
    """
    Get asset relationships using a simplified approach
    Returns a list of asset information related to the form
    """
    assets = []
    
    try:
        form_id = form_data.get('id')
        if not form_id:
            print("No form ID found in form data")
            return []
        
        print(f"=== Looking for relationships for form ID: {form_id} ===")
        
        # First, try to get all assets from the project to see what's available
        assets_url = f'https://developer.api.autodesk.com/construction/assets/v1/projects/{project_id}/assets'
        print(f"Fetching all assets from: {assets_url}")
        
        assets_response = requests.get(assets_url, headers=headers)
        print(f"Assets API response status: {assets_response.status_code}")
        
        if assets_response.ok:
            assets_data = assets_response.json()
            available_assets = assets_data.get('data', [])
            print(f"Found {len(available_assets)} assets in project")
            
            # Show first few assets for debugging
            for i, asset in enumerate(available_assets[:3]):
                asset_name = asset.get('attributes', {}).get('name', 'Unknown')
                asset_id = asset.get('id', 'Unknown')
                print(f"  Asset {i+1}: {asset_name} (ID: {asset_id})")
            
            # First, check for actual form references
            form_references = get_form_references(form_data, project_id, headers)
            if form_references:
                assets = form_references
            else:
                # Fallback to content-based search
                assets = find_asset_relationships_in_form(form_data, available_assets)
            
        else:
            print(f"Assets API request failed: {assets_response.status_code} - {assets_response.text}")
            # Fallback to content-based search
            assets = search_assets_by_form_content(form_data, project_id, headers)
        
        print(f"=== Found {len(assets)} asset relationships for form {form_id} ===")
        for asset in assets:
            print(f"  - {asset['name']} ({asset['type']}): {asset['match_reason']}")
        
        return assets
        
    except Exception as e:
        print(f"Error getting asset relationships: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def find_asset_relationships_in_form(form_data, available_assets):
    """
    Find asset relationships by analyzing form data against available assets
    """
    assets = []
    
    try:
        # Extract all text from form for matching
        form_text = ""
        
        # Get text from custom values
        custom_values = form_data.get('customValues', [])
        for item in custom_values:
            if item.get('textVal'):
                form_text += f" {item['textVal']}"
            if item.get('itemLabel'):
                form_text += f" {item['itemLabel']}"
        
        # Get text from PDF values
        pdf_values = form_data.get('pdfValues', [])
        for item in pdf_values:
            if item.get('textVal'):
                form_text += f" {item['textVal']}"
            if item.get('itemLabel'):
                form_text += f" {item['itemLabel']}"
        
        # Get text from tabular values
        tabular_values = form_data.get('tabularValues', {})
        for section_name, rows in tabular_values.items():
            form_text += f" {section_name}"
            if rows:
                for row in rows:
                    for key, value in row.items():
                        if isinstance(value, str):
                            form_text += f" {value}"
        
        form_text = form_text.lower()
        print(f"Form text for matching (first 200 chars): {form_text[:200]}...")
        
        # Match assets by name or description
        for asset in available_assets:
            asset_name = asset.get('attributes', {}).get('name', '').lower()
            asset_desc = asset.get('attributes', {}).get('description', '').lower()
            asset_id = asset.get('id', '')
            
            # Check if asset name appears in form text
            if asset_name and asset_name in form_text:
                assets.append({
                    'id': asset_id,
                    'name': asset.get('attributes', {}).get('name', 'Unknown Asset'),
                    'description': asset.get('attributes', {}).get('description', ''),
                    'type': 'name_match',
                    'match_reason': f'Asset name "{asset_name}" found in form content'
                })
            
            # Check if asset description appears in form text
            elif asset_desc and asset_desc in form_text:
                assets.append({
                    'id': asset_id,
                    'name': asset.get('attributes', {}).get('name', 'Unknown Asset'),
                    'description': asset.get('attributes', {}).get('description', ''),
                    'type': 'description_match',
                    'match_reason': f'Asset description found in form content'
                })
        
        # Check for location-based relationships
        location_id = form_data.get('locationId')
        if location_id:
            print(f"Form has location ID: {location_id}")
            for asset in available_assets:
                asset_location = asset.get('attributes', {}).get('locationId')
                if asset_location == location_id:
                    assets.append({
                        'id': asset.get('id', ''),
                        'name': asset.get('attributes', {}).get('name', 'Unknown Asset'),
                        'description': asset.get('attributes', {}).get('description', ''),
                        'type': 'location_match',
                        'match_reason': f'Same location as form (ID: {location_id})'
                    })
        
        # Check for embedded asset references in form fields
        embedded_assets = check_form_for_embedded_relationships(form_data)
        if embedded_assets:
            assets.extend(embedded_assets)
        
        # Remove duplicates based on asset ID
        unique_assets = []
        seen_ids = set()
        for asset in assets:
            if asset['id'] not in seen_ids:
                unique_assets.append(asset)
                seen_ids.add(asset['id'])
        
        return unique_assets[:5]  # Limit to 5 most relevant assets
        
    except Exception as e:
        print(f"Error finding asset relationships in form: {str(e)}")
        return []

def get_asset_details(asset_id, project_id, headers):
    """
    Get detailed asset information using Assets V2 API
    """
    try:
        # Use the Assets V2 API to get all assets and find the specific one by ID
        url = f'https://developer.api.autodesk.com/construction/assets/v2/projects/{project_id}/assets'
        response = requests.get(url, headers=headers)
        if response.ok:
            assets_data = response.json()
            assets = assets_data.get('results', [])
            
            # Find the specific asset by ID
            for asset in assets:
                if asset.get('id') == asset_id:
                    # Extract the specific fields we want
                    client_asset_id = asset.get('clientAssetId', 'Unknown Asset')
                    asset_description = asset.get('description', '')
                    location_id = asset.get('locationId', 'N/A')
                    barcode = asset.get('barcode', 'N/A')
                    
                    # Use clientAssetId as the primary name, with description as fallback
                    asset_name = client_asset_id if client_asset_id != 'Unknown Asset' else asset_description
                    
                    print(f"✅ Found asset: {asset_name} (ID: {asset_id})")
                    print(f"   Client Asset ID: {client_asset_id}")
                    print(f"   Description: {asset_description}")
                    print(f"   Location ID: {location_id}")
                    print(f"   Barcode: {barcode}")
                    
                    # Return enhanced asset info
                    return {
                        'name': asset_name,
                        'description': asset_description,
                        'clientAssetId': client_asset_id,
                        'locationId': location_id,
                        'barcode': barcode,
                        'categoryId': asset.get('categoryId', ''),
                        'statusId': asset.get('statusId', ''),
                        'isActive': asset.get('isActive', True)
                    }
            
            print(f"❌ Asset {asset_id} not found in project assets list")
            return None
        
        # If that fails, try with b. prefix
        url = f'https://developer.api.autodesk.com/construction/assets/v2/projects/b.{project_id}/assets'
        response = requests.get(url, headers=headers)
        if response.ok:
            assets_data = response.json()
            assets = assets_data.get('results', [])
            
            # Find the specific asset by ID
            for asset in assets:
                if asset.get('id') == asset_id:
                    # Extract the specific fields we want
                    client_asset_id = asset.get('clientAssetId', 'Unknown Asset')
                    asset_description = asset.get('description', '')
                    location_id = asset.get('locationId', 'N/A')
                    barcode = asset.get('barcode', 'N/A')
                    
                    # Use clientAssetId as the primary name, with description as fallback
                    asset_name = client_asset_id if client_asset_id != 'Unknown Asset' else asset_description
                    
                    print(f"✅ Found asset via b. prefix: {asset_name} (ID: {asset_id})")
                    print(f"   Client Asset ID: {client_asset_id}")
                    print(f"   Description: {asset_description}")
                    print(f"   Location ID: {location_id}")
                    print(f"   Barcode: {barcode}")
                    
                    # Return enhanced asset info
                    return {
                        'name': asset_name,
                        'description': asset_description,
                        'clientAssetId': client_asset_id,
                        'locationId': location_id,
                        'barcode': barcode,
                        'categoryId': asset.get('categoryId', ''),
                        'statusId': asset.get('statusId', ''),
                        'isActive': asset.get('isActive', True)
                    }
            
            print(f"❌ Asset {asset_id} not found in project assets list (b. prefix)")
            return None
            
        print(f"Asset details request failed: {response.status_code}")
        return None
    except Exception as e:
        print(f"Error getting asset details: {str(e)}")
        return None

def search_assets_by_form_content(form_data, project_id, headers):
    """
    Fallback method: search for assets by matching form content
    """
    assets = []
    
    try:
        # Get all assets from the project
        assets_url = f'https://developer.api.autodesk.com/construction/assets/v1/projects/{project_id}/assets'
        assets_response = requests.get(assets_url, headers=headers)
        
        if assets_response.ok:
            assets_data = assets_response.json()
            available_assets = assets_data.get('data', [])
            
            # Extract all text from form
            form_text = ""
            custom_values = form_data.get('customValues', [])
            for item in custom_values:
                if item.get('textVal'):
                    form_text += f" {item['textVal']}"
                if item.get('itemLabel'):
                    form_text += f" {item['itemLabel']}"
            
            form_text = form_text.lower()
            
            # Match assets by name or description
            for asset in available_assets:
                asset_name = asset.get('attributes', {}).get('name', '').lower()
                asset_desc = asset.get('attributes', {}).get('description', '').lower()
                
                if asset_name and asset_name in form_text:
                    assets.append({
                        'id': asset.get('id', ''),
                        'name': asset.get('attributes', {}).get('name', 'Unknown Asset'),
                        'description': asset.get('attributes', {}).get('description', ''),
                        'type': 'content_match',
                        'match_reason': f'Asset name found in form content'
                    })
        
    except Exception as e:
        print(f"Error in content-based asset search: {str(e)}")
    
    return assets

def check_form_for_embedded_relationships(form_data):
    """
    Check if the form data contains any embedded relationship information
    """
    relationships = []
    
    try:
        # Check for common relationship field names in custom values
        custom_values = form_data.get('customValues', [])
        for item in custom_values:
            label = item.get('itemLabel', '').lower()
            value = None
            
            # Get the value based on type
            if item.get('textVal'):
                value = item['textVal']
            elif item.get('numberVal') is not None:
                value = str(item['numberVal'])
            elif item.get('dateVal'):
                value = item['dateVal']
            
            # Look for asset ID patterns (like the [1484849] in the example)
            if value and '[' in value and ']' in value:
                # Extract potential asset ID
                import re
                asset_id_match = re.search(r'\[([^\]]+)\]', value)
                if asset_id_match:
                    asset_id = asset_id_match.group(1)
                    relationships.append({
                        'id': asset_id,
                        'name': value.split('[')[0].strip(),
                        'description': f'Found in field: {item.get("itemLabel", "")}',
                        'type': 'embedded_reference',
                        'match_reason': f'Asset ID found in form field: {asset_id}'
                    })
            
            # Also check for fields that might contain asset references
            if value and any(keyword in label for keyword in ['asset', 'equipment', 'component', 'reference']):
                relationships.append({
                    'id': None,
                    'name': value,
                    'description': item.get('itemLabel', 'Asset Reference'),
                    'type': 'field_reference',
                    'match_reason': f'Found in field: {item.get("itemLabel", "")}'
                })
        
        # Check for any relationship metadata in the form
        if 'relationships' in form_data:
            print(f"Form has relationships metadata: {form_data['relationships']}")
            # Process the relationships metadata if it exists
        
        # Check for any asset-related metadata
        if 'assetId' in form_data:
            relationships.append({
                'id': form_data['assetId'],
                'name': 'Referenced Asset',
                'description': 'Direct asset reference in form metadata',
                'type': 'metadata_reference',
                'match_reason': 'Asset ID in form metadata'
            })
        
        return relationships
        
    except Exception as e:
        print(f"Error checking for embedded relationships: {str(e)}")
        return []

@app.route('/api/forms/<project_id>')
def get_project_forms_api(project_id):
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    headers = {
        'Authorization': f'Bearer {session["access_token"]}',
        'Content-Type': 'application/json'
    }
    
    # Get the selected hub ID from session to determine project type
    selected_hub_id = session.get('selected_hub_id')
    if not selected_hub_id:
        return jsonify({'error': 'No hub selected'}), 400
    
    try:
        print(f"Project ID: {project_id}")
        print(f"Selected Hub ID: {selected_hub_id}")
        
        # For ACC projects, use the ACC forms API with region-specific endpoints
        # Remove "b." prefix if it exists for ACC API
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        
        # Get region from request args or use US as default
        region = request.args.get('region', 'US').upper()
        region_path = ''
        if region == 'AU':
            region_path = '/au'
        elif region == 'EMEA':
            region_path = '/emea'
        # else US or default - no additional path
        
        # Use the Construction Forms API for ACC projects
        url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms'
        print(f"Using Construction Forms API: {url}")
        print(f"Original project ID: {project_id}, ACC project ID: {acc_project_id}, Region: {region}")
        
        print(f"Making request to: {url}")
        print(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if not response.ok:
            print(f"Error response: {response.text}")
            return jsonify({'error': f'API request failed: {response.status_code} - {response.text}'}), response.status_code
        
        response.raise_for_status()
        forms_data = response.json()
        print(f"Forms data: {forms_data}")
        print(f"Forms data type: {type(forms_data)}")
        print(f"Forms data keys: {list(forms_data.keys()) if isinstance(forms_data, dict) else 'Not a dict'}")
        if isinstance(forms_data, dict) and 'data' in forms_data:
            print(f"Number of forms in data: {len(forms_data['data'])}")
            if forms_data['data']:
                print(f"First form structure: {forms_data['data'][0]}")
        
        # Check if forms_data has the expected structure
        if not isinstance(forms_data, dict):
            print(f"Unexpected forms_data type: {type(forms_data)}")
            return jsonify({'error': 'Invalid response format'}), 500
            
        if 'data' not in forms_data:
            print(f"Forms data missing 'data' key. Available keys: {list(forms_data.keys())}")
            return jsonify({'error': 'Response missing forms data'}), 500
        
        forms = []
        if 'data' in forms_data:
            print(f"Processing {len(forms_data['data'])} forms from API response")
            for i, form in enumerate(forms_data['data']):
                try:
                    print(f"Processing form {i+1}: {form}")
                    
                    # Extract asset relationships using the enhanced approach from form test
                    assets = get_form_asset_relationships(form, acc_project_id, headers)
                    if assets:
                        print(f"Found {len(assets)} asset relationships for form {form.get('id', 'unknown')}: {assets}")
                    
                    # For Extension of Time Claim forms, get detailed relationship information
                    related_assets = []
                    form_name = form.get('attributes', {}).get('name', form.get('name', '')).lower()
                    if 'extension of time claim' in form_name or 'extension of time' in form_name:
                        print(f"=== Getting detailed relationships for Extension form: {form.get('id')} ===")
                        
                        # Get detailed form data first (like in form test)
                        detailed_form_data = get_form_details(form.get('id'), acc_project_id, headers)
                        if detailed_form_data:
                            print(f"Got detailed form data for {form.get('id')}")
                            # Use the same logic as form test to find relationships
                            detailed_assets = find_relationships_for_form(form.get('id'), acc_project_id, headers)
                            if detailed_assets:
                                related_assets = detailed_assets
                                print(f"Found {len(detailed_assets)} detailed relationships for Extension form")
                        else:
                            print(f"Could not get detailed form data for {form.get('id')}")
                    
                    # Check if the form has the expected structure
                    if 'attributes' in form:
                        # Standard structure with attributes
                        form_info = {
                            'id': form['id'],
                            'name': form['attributes']['name'],
                            'created_at': form['attributes'].get('created_at'),
                            'status': form['attributes'].get('status', 'unknown'),
                            'assets': assets,
                            'related_assets': related_assets  # Add detailed relationship data
                        }
                    else:
                        # Direct structure (no attributes wrapper)
                        form_info = {
                            'id': form['id'],
                            'name': form.get('name', 'Unnamed Form'),
                            'created_at': form.get('createdAt') or form.get('created_at'),
                            'status': form.get('status', 'unknown'),
                            'assets': assets,
                            'related_assets': related_assets  # Add detailed relationship data
                        }
                    
                    forms.append(form_info)
                    print(f"Successfully processed form: {form_info}")
                except KeyError as e:
                    print(f"Error processing form {i+1}: Missing key {e}")
                    print(f"Form data: {form}")
                except Exception as e:
                    print(f"Error processing form {i+1}: {str(e)}")
                    print(f"Form data: {form}")
        
        print(f"Successfully processed {len(forms)} forms")
        return jsonify(forms)
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return jsonify({'error': f'Request failed: {str(e)}'}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/forms/<form_id>/download')
def download_form_api(form_id):
    # Get project_id from query parameter
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': 'Missing project_id parameter'}), 400
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    headers = {
        'Authorization': f'Bearer {session["access_token"]}',
        'Content-Type': 'application/json'
    }
    
    # Get the selected hub ID from session to determine project type
    selected_hub_id = session.get('selected_hub_id')
    if not selected_hub_id:
        return jsonify({'error': 'No hub selected'}), 400
    
    try:
        print(f"Downloading form {form_id} from project {project_id}")
        print(f"Selected hub ID: {selected_hub_id}")
        
        # For ACC forms, use the ACC forms API
        # Remove "b." prefix if it exists for ACC API
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        print(f"Original project ID: {project_id}, ACC project ID: {acc_project_id}")
        
        url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms/{form_id}/content'
        print(f"Making request to: {url}")
        print(f"Headers: {headers}")
        
        content_response = requests.get(url, headers=headers)
        print(f"Response status: {content_response.status_code}")
        print(f"Response headers: {dict(content_response.headers)}")
        
        content_response.raise_for_status()
        
        # Return the form content as a downloadable file
        return Response(
            content_response.content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=form_{form_id}.pdf'
            }
        )
    except Exception as e:
        print(f"Error downloading form: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/forms/<form_id>/export-pdf', methods=['GET', 'POST'])
def export_form_pdf(form_id):
    # Get project_id and filename from parameters (query params for GET, form data for POST)
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        filename = request.form.get('filename', f'form_{form_id}.pdf')
        # Get export settings
        logo_data = request.form.get('logo_data')
        logo_position = request.form.get('logo_position', 'top-left')
        logo_size = request.form.get('logo_size', 'medium')
        pdf_orientation = request.form.get('pdf_orientation', 'portrait')
        pdf_margin = request.form.get('pdf_margin', 'medium')
        include_page_numbers = request.form.get('include_page_numbers', 'true').lower() == 'true'
        include_timestamp = request.form.get('include_timestamp', 'true').lower() == 'true'
    else:
        project_id = request.args.get('project_id')
        filename = request.args.get('filename', f'form_{form_id}.pdf')
        logo_data = None
        logo_position = 'top-left'
        logo_size = 'medium'
        pdf_orientation = 'portrait'
        pdf_margin = 'medium'
        include_page_numbers = True
        include_timestamp = True
    
    if not project_id:
        return jsonify({'error': 'Missing project_id parameter'}), 400
    
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Remove the "b." prefix from the project ID if it exists
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        headers = get_autodesk_headers(session['access_token'])
        
        # Project name removed - will not display in PDF
        
        # Get form data (reuse logic from view_form)
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms'
        forms_response = requests.get(forms_url, headers=headers)
        if not forms_response.ok:
            return jsonify({'error': f'Failed to get forms: {forms_response.status_code}'}), forms_response.status_code
        
        forms_data = forms_response.json()
        
        # Find the specific form
        form_data = None
        for form in forms_data.get('data', []):
            if form['id'] == form_id:
                form_data = form
                break
        
        if not form_data:
            return jsonify({'error': f'Form with ID {form_id} not found'}), 404
        
        # Process form data (reuse logic from view_form)
        form_info = {
            'name': form_data.get('name', 'Unnamed Form'),
            'sections': []
        }
        
        # Process form data (complete version - same as view_form)
        id_mapping = {}
        if form_data.get('formTemplate') and form_data['formTemplate'].get('id_mapping'):
            id_mapping = form_data['formTemplate']['id_mapping']
        elif form_data.get('form_template') and form_data['form_template'].get('id_mapping'):
            id_mapping = form_data['form_template']['id_mapping']
        
        def get_label(item_id, fallback):
            return id_mapping.get(item_id, fallback)
        
        # Process all form values
        section_map = {}
        
        # Process pdf_values
        for item in form_data.get('pdfValues', []):
            section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'General'))
            if section_title not in section_map:
                section_map[section_title] = []
            
            if item.get('dateVal'):
                ftype, fval = 'date', item['dateVal']
            elif item.get('numVal') is not None:
                ftype, fval = 'number', item['numVal']
            elif item.get('boolVal') is not None:
                ftype, fval = 'bool', item['boolVal']
            elif item.get('listVal'):
                ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
            elif item.get('objVal'):
                ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
            elif item.get('textVal'):
                ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
            else:
                ftype, fval = 'text', ''
            
            section_map[section_title].append({
                'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                'type': ftype,
                'value': fval
            })
        
        # Process tabular_values
        for section, rows in form_data.get('tabularValues', {}).items():
            section_title = get_label(section, section)
            fields = []
            if rows:
                for idx, row in enumerate(rows, 1):
                    for key, value in row.items():
                        label = get_label(key, key)
                        if isinstance(value, bool):
                            ftype = 'bool'
                        elif isinstance(value, (int, float)):
                            ftype = 'number'
                        elif isinstance(value, list):
                            ftype = 'list'
                            value = [get_label(v, v) for v in value]
                        elif isinstance(value, dict):
                            ftype = 'object'
                            value = {get_label(k, k): get_label(v, v) for k, v in value.items()}
                        else:
                            ftype = 'text'
                            value = get_label(value, value)
                        fields.append({
                            'label': f"{label} (Row {idx})",
                            'type': ftype,
                            'value': value
                        })
            if fields:
                section_map[section_title] = section_map.get(section_title, []) + fields
        
        # Process custom_values
        for item in form_data.get('customValues', []):
            section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'Custom Fields'))
            if section_title not in section_map:
                section_map[section_title] = []
            
            if item.get('dateVal'):
                ftype, fval = 'date', item['dateVal']
            elif item.get('numVal') is not None:
                ftype, fval = 'number', item['numVal']
            elif item.get('boolVal') is not None:
                ftype, fval = 'bool', item['boolVal']
            elif item.get('listVal'):
                ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
            elif item.get('objVal'):
                ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
            elif item.get('textVal'):
                ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
            else:
                ftype, fval = 'text', ''
            
            section_map[section_title].append({
                'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                'type': ftype,
                'value': fval
            })
        
        # Convert section map to list of sections
        form_info['sections'] = [{'title': title, 'fields': fields} for title, fields in section_map.items()]
        
        # Handle logo with settings
        logo_html = ""
        if logo_data:
            # Determine logo size
            size_map = {'small': '50px', 'medium': '100px', 'large': '150px'}
            logo_width = size_map.get(logo_size, '100px')
            
            # Determine logo position and styling - align with form name
            position_styles = {
                'top-left': f'position: absolute; top: 5px; left: 20px; max-width: {logo_width}; max-height: {logo_width};',
                'top-right': f'position: absolute; top: 5px; right: 20px; max-width: {logo_width}; max-height: {logo_width};',
                'bottom-left': f'position: absolute; bottom: 20px; left: 20px; max-width: {logo_width}; max-height: {logo_width};',
                'bottom-right': f'position: absolute; bottom: 20px; right: 20px; max-width: {logo_width}; max-height: {logo_width};'
            }
            
            logo_style = position_styles.get(logo_position, position_styles['top-left'])
            logo_html = f'<img src="{logo_data}" style="{logo_style}">'
        
        # Generate HTML for PDF
        # Determine page settings
        margin_map = {'small': '0.5in', 'medium': '1in', 'large': '1.5in'}
        page_margin = margin_map.get(pdf_margin, '1in')
        page_size = 'A4 landscape' if pdf_orientation == 'landscape' else 'A4'
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{filename}</title>
            <style>
                @page {{ margin: {page_margin}; size: {page_size}; }}
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px;
                    font-size: 12px;
                    line-height: 1.4;
                    position: relative;
                }}
                .form-header {{ 
                    margin-bottom: 30px; 
                    border-bottom: 2px solid #333;
                    padding-bottom: 15px;
                    overflow: hidden;
                }}
                .form-header h1 {{
                    margin: 0 0 10px 0;
                    font-size: 24px;
                    font-weight: bold;
                    text-align: center;
                }}
                .form-header p {{
                    text-align: center;
                    margin: 0;
                }}
                .form-section {{ 
                    margin-bottom: 25px; 
                    page-break-inside: avoid;
                }}
                .section-title {{ 
                    font-weight: bold; 
                    font-size: 16px; 
                    margin-bottom: 15px; 
                    border-bottom: 1px solid #333; 
                    padding: 8px;
                    background-color: #f5f5f5;
                }}
                .form-field {{ 
                    margin-bottom: 12px; 
                    page-break-inside: avoid;
                }}
                .field-label {{ 
                    font-weight: bold; 
                    margin-bottom: 5px;
                    font-size: 11px;
                }}
                .field-value {{ 
                    padding: 8px; 
                    border: 1px solid #ccc; 
                    background-color: #f9f9f9; 
                    min-height: 20px;
                    font-size: 11px;
                    word-wrap: break-word;
                }}
                {f'@page {{ @bottom-center {{ content: counter(page); font-size: 10px; color: #666; }} }}' if include_page_numbers else ''}
            </style>
        </head>
        <body>
            <div class="form-header">
                {logo_html}
                <h1>{form_info['name']}</h1>
                {f'<p style="text-align: right; font-size: 10px; color: #666;">Exported: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>' if include_timestamp else ''}
            </div>
            {''.join(f'''
            <div class="form-section">
                <div class="section-title">{i+1}. {section['title']}</div>
                {''.join(f'''
                <div class="form-field">
                    <div class="field-label">{j+1}. {field['label']}</div>
                    <div class="field-value">{field['value'] or 'N/A'}</div>
                </div>
                ''' for j, field in enumerate(section['fields']))}
            </div>
            ''' for i, section in enumerate(form_info['sections']))}
        </body>
        </html>
        """
        
        # Convert HTML to PDF using pdfkit
        try:
            import pdfkit
            config = pdfkit.configuration(wkhtmltopdf=find_wkhtmltopdf())
            pdf_bytes = pdfkit.from_string(html_content, False, configuration=config)
            
            # Return PDF with proper filename
            return Response(pdf_bytes, 
                           mimetype='application/pdf',
                           headers={'Content-Disposition': f'attachment; filename="{filename}"'})
        except ImportError:
            return jsonify({'error': 'PDF generation not available. Please install pdfkit and wkhtmltopdf.'}), 500
        except Exception as e:
            return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500
    
    except Exception as e:
        print(f"Error in export_form_pdf: {str(e)}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/settings/upload-logo', methods=['POST'])
def upload_logo():
    """Upload and store company logo for PDF exports"""
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if 'logo' not in request.files:
            return jsonify({'error': 'No logo file provided'}), 400
        
        logo_file = request.files['logo']
        if logo_file.filename == '':
            return jsonify({'error': 'No logo file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
        if not logo_file.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)):
            return jsonify({'error': 'Invalid file type. Please upload an image file.'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Save logo file
        logo_filename = f"company_logo_{int(time.time())}.{logo_file.filename.split('.')[-1]}"
        logo_path = os.path.join(upload_dir, logo_filename)
        logo_file.save(logo_path)
        
        # Store logo path in session
        session['company_logo_path'] = logo_path
        
        return jsonify({
            'success': True,
            'message': 'Logo uploaded successfully',
            'logo_path': logo_path
        })
        
    except Exception as e:
        print(f"Error uploading logo: {str(e)}")
        return jsonify({'error': f'Failed to upload logo: {str(e)}'}), 500

@app.route('/api/settings/get-logo', methods=['GET'])
def get_logo():
    """Get the current company logo"""
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    logo_path = session.get('company_logo_path')
    if logo_path and os.path.exists(logo_path):
        return send_file(logo_path, mimetype='image/*')
    else:
        return jsonify({'error': 'No logo found'}), 404

@app.route('/api/forms/export-zip', methods=['GET', 'POST'])
def export_forms_zip():
    # Get parameters from query params (GET) or form data (POST)
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        form_ids = request.form.get('form_ids', '')
        filenames = request.form.get('filenames', '')
        # New settings parameters
        logo_data = request.form.get('logo_data')
        logo_position = request.form.get('logo_position', 'top-left')
        logo_size = request.form.get('logo_size', 'medium')
        pdf_orientation = request.form.get('pdf_orientation', 'portrait')
        pdf_margin = request.form.get('pdf_margin', 'medium')
        include_page_numbers = request.form.get('include_page_numbers', 'true').lower() == 'true'
        include_timestamp = request.form.get('include_timestamp', 'true').lower() == 'true'
        # Legacy parameters (for backward compatibility)
        include_logo = request.form.get('include_logo', 'false').lower() == 'true'
        logo_file = request.files.get('logo')
    else:
        project_id = request.args.get('project_id')
        form_ids = request.args.get('form_ids', '')
        filenames = request.args.get('filenames', '')
        # New settings parameters
        logo_data = request.args.get('logo_data')
        logo_position = request.args.get('logo_position', 'top-left')
        logo_size = request.args.get('logo_size', 'medium')
        pdf_orientation = request.args.get('pdf_orientation', 'portrait')
        pdf_margin = request.args.get('pdf_margin', 'medium')
        include_page_numbers = request.args.get('include_page_numbers', 'true').lower() == 'true'
        include_timestamp = request.args.get('include_timestamp', 'true').lower() == 'true'
        # Legacy parameters
        include_logo = False
        logo_file = None
    
    if not project_id or not form_ids:
        return jsonify({'error': 'Missing project_id or form_ids parameter'}), 400
    
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Parse form IDs and filenames
        form_id_list = form_ids.split(',')
        filename_list = filenames.split(',') if filenames else []
        
        if not form_id_list:
            return jsonify({'error': 'No form IDs provided'}), 400
        
        # Ensure we have the same number of filenames as form IDs
        if filename_list and len(filename_list) != len(form_id_list):
            return jsonify({'error': 'Number of filenames does not match number of form IDs'}), 400
        
        # Remove the "b." prefix from the project ID if it exists
        acc_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        headers = get_autodesk_headers(session['access_token'])
        
        # Get project details to display the actual project name
        project_name = "Unknown Project"
        try:
            project_response = requests.get(
                f'https://developer.api.autodesk.com/project/v1/projects/{acc_project_id}',
                headers=headers
            )
            if project_response.ok:
                project_data = project_response.json()
                project_name = project_data['data']['attributes']['name']
        except Exception as e:
            print(f"Warning: Could not fetch project name: {e}")
            project_name = "Unknown Project"
        
        # Get all forms data
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{acc_project_id}/forms'
        forms_response = requests.get(forms_url, headers=headers)
        if not forms_response.ok:
            return jsonify({'error': f'Failed to get forms: {forms_response.status_code}'}), forms_response.status_code
        
        forms_data = forms_response.json()
        
        # Create a temporary ZIP file
        import tempfile
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, form_id in enumerate(form_id_list):
                # Find the specific form
                form_data = None
                for form in forms_data.get('data', []):
                    if form['id'] == form_id:
                        form_data = form
                        break
                
                if not form_data:
                    continue  # Skip if form not found
                
                # Process form data (reuse logic from export_form_pdf)
                form_info = {
                    'name': form_data.get('name', 'Unnamed Form'),
                    'sections': []
                }
                
                # Process form data (complete version - same as view_form)
                id_mapping = {}
                if form_data.get('formTemplate') and form_data['formTemplate'].get('id_mapping'):
                    id_mapping = form_data['formTemplate']['id_mapping']
                elif form_data.get('form_template') and form_data['form_template'].get('id_mapping'):
                    id_mapping = form_data['form_template']['id_mapping']
                
                def get_label(item_id, fallback):
                    return id_mapping.get(item_id, fallback)
                
                # Process all form values
                section_map = {}
                
                # Process pdf_values
                for item in form_data.get('pdfValues', []):
                    section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'General'))
                    if section_title not in section_map:
                        section_map[section_title] = []
                    
                    if item.get('dateVal'):
                        ftype, fval = 'date', item['dateVal']
                    elif item.get('numVal') is not None:
                        ftype, fval = 'number', item['numVal']
                    elif item.get('boolVal') is not None:
                        ftype, fval = 'bool', item['boolVal']
                    elif item.get('listVal'):
                        ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
                    elif item.get('objVal'):
                        ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
                    elif item.get('textVal'):
                        ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
                    else:
                        ftype, fval = 'text', ''
                    
                    section_map[section_title].append({
                        'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                        'type': ftype,
                        'value': fval
                    })
                
                # Process tabular_values
                for section, rows in form_data.get('tabularValues', {}).items():
                    section_title = get_label(section, section)
                    fields = []
                    if rows:
                        for idx, row in enumerate(rows, 1):
                            for key, value in row.items():
                                label = get_label(key, key)
                                if isinstance(value, bool):
                                    ftype = 'bool'
                                elif isinstance(value, (int, float)):
                                    ftype = 'number'
                                elif isinstance(value, list):
                                    ftype = 'list'
                                    value = [get_label(v, v) for v in value]
                                elif isinstance(value, dict):
                                    ftype = 'object'
                                    value = {get_label(k, k): get_label(v, v) for k, v in value.items()}
                                else:
                                    ftype = 'text'
                                    value = get_label(value, value)
                                fields.append({
                                    'label': f"{label} (Row {idx})",
                                    'type': ftype,
                                    'value': value
                                })
                    if fields:
                        section_map[section_title] = section_map.get(section_title, []) + fields
                    
                # Process custom_values
                for item in form_data.get('customValues', []):
                    section_title = get_label(item.get('sectionId', ''), item.get('sectionLabel', 'Custom Fields'))
                    if section_title not in section_map:
                        section_map[section_title] = []
                    
                    if item.get('dateVal'):
                        ftype, fval = 'date', item['dateVal']
                    elif item.get('numVal') is not None:
                        ftype, fval = 'number', item['numVal']
                    elif item.get('boolVal') is not None:
                        ftype, fval = 'bool', item['boolVal']
                    elif item.get('listVal'):
                        ftype, fval = 'list', [get_label(v, v) for v in item['listVal']]
                    elif item.get('objVal'):
                        ftype, fval = 'object', {get_label(k, k): get_label(v, v) for k, v in item['objVal'].items()}
                    elif item.get('textVal'):
                        ftype, fval = 'text', get_label(item['textVal'], item['textVal'])
                    else:
                        ftype, fval = 'text', ''
                    
                    section_map[section_title].append({
                        'label': get_label(item.get('itemId', ''), item.get('itemLabel', 'Field')),
                        'type': ftype,
                        'value': fval
                    })
                
                # Convert section map to list of sections
                form_info['sections'] = [{'title': title, 'fields': fields} for title, fields in section_map.items()]
                
                # Handle logo with settings (same as export_form_pdf)
                logo_html = ""
                if logo_data:
                    # Determine logo size
                    size_map = {'small': '50px', 'medium': '100px', 'large': '150px'}
                    logo_width = size_map.get(logo_size, '100px')
                    
                    # Determine logo position and styling - align with form name
                    position_styles = {
                        'top-left': f'position: absolute; top: 5px; left: 20px; max-width: {logo_width}; max-height: {logo_width};',
                        'top-right': f'position: absolute; top: 5px; right: 20px; max-width: {logo_width}; max-height: {logo_width};',
                        'bottom-left': f'position: absolute; bottom: 20px; left: 20px; max-width: {logo_width}; max-height: {logo_width};',
                        'bottom-right': f'position: absolute; bottom: 20px; right: 20px; max-width: {logo_width}; max-height: {logo_width};'
                    }
                    
                    logo_style = position_styles.get(logo_position, position_styles['top-left'])
                    logo_html = f'<img src="{logo_data}" style="{logo_style}">'
                
                # Use custom filename if provided, otherwise generate default
                if filename_list and i < len(filename_list):
                    filename = filename_list[i].replace('/', '_').replace('\\', '_').replace(':', '_')
                    filename = f"{filename}.pdf"
                else:
                    filename = form_info['name'].replace('/', '_').replace('\\', '_').replace(':', '_')
                    filename = f"{filename}_{form_id[:8]}.pdf"
                
                # Generate HTML for PDF (same as export_form_pdf)
                # Determine page settings
                margin_map = {'small': '0.5in', 'medium': '1in', 'large': '1.5in'}
                page_margin = margin_map.get(pdf_margin, '1in')
                page_size = 'A4 landscape' if pdf_orientation == 'landscape' else 'A4'
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{filename}</title>
                    <style>
                        @page {{ margin: {page_margin}; size: {page_size}; }}
                        body {{ 
                            font-family: Arial, sans-serif; 
                            margin: 0; 
                            padding: 20px;
                            font-size: 12px;
                            line-height: 1.4;
                            position: relative;
                        }}
                        .form-header {{ 
                            margin-bottom: 30px; 
                            border-bottom: 2px solid #333;
                            padding-bottom: 15px;
                            overflow: hidden;
                        }}
                        .form-header h1 {{
                            margin: 0 0 10px 0;
                            font-size: 24px;
                            font-weight: bold;
                            text-align: center;
                        }}
                        .form-header p {{
                            text-align: center;
                            margin: 0;
                        }}
                        .form-section {{ 
                            margin-bottom: 25px; 
                            page-break-inside: avoid;
                        }}
                        .section-title {{ 
                            font-weight: bold; 
                            font-size: 16px; 
                            margin-bottom: 15px; 
                            border-bottom: 1px solid #333; 
                            padding: 8px;
                            background-color: #f5f5f5;
                        }}
                        .form-field {{ 
                            margin-bottom: 12px; 
                            page-break-inside: avoid;
                        }}
                        .field-label {{ 
                            font-weight: bold; 
                            margin-bottom: 5px;
                            font-size: 11px;
                        }}
                        .field-value {{ 
                            padding: 8px; 
                            border: 1px solid #ccc; 
                            background-color: #f9f9f9; 
                            min-height: 20px;
                            font-size: 11px;
                            word-wrap: break-word;
                        }}
                        {f'@page {{ @bottom-center {{ content: counter(page); font-size: 10px; color: #666; }} }}' if include_page_numbers else ''}
                    </style>
                </head>
                <body>
                    <div class="form-header">
                        {logo_html}
                        <h1>{form_info['name']}</h1>
                        {f'<p style="text-align: right; font-size: 10px; color: #666;">Exported: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>' if include_timestamp else ''}
                    </div>
                    {''.join(f'''
                    <div class="form-section">
                        <div class="section-title">{i+1}. {section['title']}</div>
                        {''.join(f'''
                        <div class="form-field">
                            <div class="field-label">{j+1}. {field['label']}</div>
                            <div class="field-value">{field['value'] or 'N/A'}</div>
                        </div>
                        ''' for j, field in enumerate(section['fields']))}
                    </div>
                    ''' for i, section in enumerate(form_info['sections']))}
                </body>
                </html>
                """
                
                # Convert HTML to PDF and add to ZIP
                try:
                    import pdfkit
                    config = pdfkit.configuration(wkhtmltopdf=find_wkhtmltopdf())
                    pdf_bytes = pdfkit.from_string(html_content, False, configuration=config)
                    
                    # Add PDF to ZIP
                    zip_file.writestr(filename, pdf_bytes)
                    
                except Exception as e:
                    print(f"Error generating PDF for form {form_id}: {str(e)}")
                    # Add error file to ZIP instead
                    error_content = f"Error generating PDF for form: {form_info['name']}\nError: {str(e)}"
                    zip_file.writestr(f"ERROR_{filename}", error_content)
        
        # Return the ZIP file
        zip_buffer.seek(0)
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename="forms_export_{len(form_id_list)}_forms.zip"'}
        )
    
    except Exception as e:
        print(f"Error in export_forms_zip: {str(e)}")
        return jsonify({'error': f'ZIP export failed: {str(e)}'}), 500

def get_writable_relationships(headers):
    """
    Get the list of entity types that can have relationships with each other
    """
    try:
        url = 'https://developer.api.autodesk.com/bim360/relationship/v2/utility/relationships:writable'
        print(f"Checking writable relationships from: {url}")
        
        response = requests.get(url, headers=headers)
        print(f"Writable relationships response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"Writable relationships data: {data}")
            return data
        else:
            print(f"Writable relationships request failed: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Error getting writable relationships: {str(e)}")
        return []

def get_form_entity_info(form_data, project_id, headers):
    """
    Determine the entity type and domain for forms in the relationship service
    """
    try:
        # Based on the documentation, forms might be in different domains
        # Let's check what entity types are available and see if we can identify forms
        
        # Common form entity types and domains to try
        possible_form_entities = [
            {'domain': 'autodesk-bim360-documentmanagement', 'type': 'documentlineage'},
            {'domain': 'autodesk-construction-forms', 'type': 'form'},
            {'domain': 'autodesk-bim360-forms', 'type': 'form'},
            {'domain': 'autodesk-construction', 'type': 'form'}
        ]
        
        # Try to get the form ID in different formats
        form_id = form_data.get('id')
        
        # Check if the form ID is already in URN format
        if form_id.startswith('urn:'):
            # It's already in the correct format
            return {
                'id': form_id,
                'domain': 'autodesk-construction-forms',  # Most likely domain for ACC forms
                'type': 'form'
            }
        else:
            # Try to construct the URN format
            # ACC forms typically use: urn:adsk.wipprod:dm.lineage:formId
            urn_form_id = f'urn:adsk.wipprod:dm.lineage:{form_id}'
            return {
                'id': urn_form_id,
                'domain': 'autodesk-construction-forms',
                'type': 'form'
            }
            
    except Exception as e:
        print(f"Error getting form entity info: {str(e)}")
        return None

def extract_asset_from_relationship_entity(entity, project_id, headers, relationship_id=None):
    """
    Extract asset information from a relationship entity
    """
    try:
        entity_id = entity.get('id')
        entity_type = entity.get('type')
        entity_domain = entity.get('domain')
        
        print(f"Processing entity: {entity_type} - {entity_id} (domain: {entity_domain})")
        
        if entity_type == 'asset':
            # Get detailed asset information
            asset_details = get_asset_details(entity_id, project_id, headers)
            if asset_details:
                return {
                    'id': entity_id,
                    'name': asset_details.get('name', 'Unknown Asset'),
                    'description': asset_details.get('description', ''),
                    'type': 'relationship_service',
                    'match_reason': f'Direct relationship via {entity_domain}',
                    'relationship_id': relationship_id
                }
            else:
                # Return basic info if we can't get details
                return {
                    'id': entity_id,
                    'name': 'Unknown Asset',
                    'description': f'Asset from {entity_domain}',
                    'type': 'relationship_service',
                    'match_reason': f'Direct relationship via {entity_domain} (ID: {entity_id})',
                    'relationship_id': relationship_id
                }
        
        return None
        
    except Exception as e:
        print(f"Error extracting asset from relationship entity: {str(e)}")
        return None

def get_form_references(form_data, project_id, headers):
    """
    Check if the form has any references to other entities (assets, issues, etc.)
    using the correct ACC Relationship Service API and form relationships structure
    """
    references = []
    
    try:
        form_id = form_data.get('id')
        print(f"=== Checking references for form ID: {form_id} ===")
        
        # First, let's see what entity types can have relationships
        writable_relationships = get_writable_relationships(headers)
        
        # Get the form entity information
        form_entity = get_form_entity_info(form_data, project_id, headers)
        if form_entity:
            print(f"Form entity info: {form_entity}")
        
        # Check if the form data contains any reference information
        print(f"Form data keys: {list(form_data.keys())}")
        
        # NEW: Check for relationships.fields.data structure (as shown in user's code)
        if 'relationships' in form_data:
            print(f"Form has relationships field: {form_data['relationships']}")
            relationships_data = form_data['relationships']
            
            if 'fields' in relationships_data and 'data' in relationships_data['fields']:
                print(f"Found relationships.fields.data structure")
                fields_data = relationships_data['fields']['data']
                
                for field in fields_data:
                    print(f"Processing relationship field: {field}")
                    
                    if 'relationship' in field:
                        relationship = field['relationship']
                        
                        # Check for asset references in field definition
                        if 'fieldDefinition' in relationship:
                            field_def = relationship['fieldDefinition']
                            field_name = field_def.get('name', '').lower()
                            
                            print(f"Field definition name: {field_name}")
                            
                            # Look for asset-related fields
                            if 'asset' in field_name:
                                print(f"Found asset field: {field_name}")
                                
                                # Check for relatedAsset data
                                if 'relatedAsset' in relationship and 'data' in relationship['relatedAsset']:
                                    asset_data = relationship['relatedAsset']['data']
                                    asset_id = asset_data.get('id')
                                    
                                    if asset_id:
                                        print(f"Found related asset ID: {asset_id}")
                                        
                                        # Get detailed asset information
                                        asset_details = get_asset_details(asset_id, project_id, headers)
                                        if asset_details:
                                            references.append({
                                                'id': asset_id,
                                                'name': asset_details.get('name', 'Unknown Asset'),
                                                'description': asset_details.get('description', ''),
                                                'type': 'form_relationship_field',
                                                'match_reason': f'Found in relationship field: {field_name}',
                                                'relationship_id': None,  # This is from form structure, not relationship service
                                                'field_name': field_name
                                            })
                                        else:
                                            references.append({
                                                'id': asset_id,
                                                'name': 'Unknown Asset',
                                                'description': f'Asset from relationship field: {field_name}',
                                                'type': 'form_relationship_field',
                                                'match_reason': f'Found in relationship field: {field_name} (ID: {asset_id})',
                                                'relationship_id': None,
                                                'field_name': field_name
                                            })
        
        # Look for common reference fields in the form data
        if 'references' in form_data:
            print(f"Form has references field: {form_data['references']}")
            references.extend(process_form_references(form_data['references'], project_id, headers))
        
        if 'relatedItems' in form_data:
            print(f"Form has relatedItems field: {form_data['relatedItems']}")
            references.extend(process_form_references(form_data['relatedItems'], project_id, headers))
        
        # Try to get form details with references included
        # Try multiple endpoints to get form data with relationships
        form_endpoints = [
            f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms/{form_id}',
            f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms/{form_id}?include=relationships',
            f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms/{form_id}?include=relationships,fields',
            f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms/{form_id}/relationships'
        ]
        
        detailed_form = None
        for endpoint in form_endpoints:
            print(f"Trying form endpoint: {endpoint}")
            form_response = requests.get(endpoint, headers=headers)
            print(f"Form endpoint response status: {form_response.status_code}")
            
            if form_response.ok:
                detailed_form = form_response.json()
                print(f"Successfully got form data from: {endpoint}")
                print(f"Detailed form data keys: {list(detailed_form.keys())}")
                break
            else:
                print(f"Form endpoint failed: {form_response.status_code} - {form_response.text}")
        
        if detailed_form:
            # Check for relationships.fields.data in detailed form
            if 'relationships' in detailed_form:
                print(f"Detailed form has relationships field: {detailed_form['relationships']}")
                detailed_relationships = detailed_form['relationships']
                
                if 'fields' in detailed_relationships and 'data' in detailed_relationships['fields']:
                    print(f"Found relationships.fields.data in detailed form")
                    detailed_fields_data = detailed_relationships['fields']['data']
                    
                    for field in detailed_fields_data:
                        print(f"Processing detailed relationship field: {field}")
                        
                        if 'relationship' in field:
                            relationship = field['relationship']
                            
                            if 'fieldDefinition' in relationship:
                                field_def = relationship['fieldDefinition']
                                field_name = field_def.get('name', '').lower()
                                
                                print(f"Detailed field definition name: {field_name}")
                                
                                if 'asset' in field_name:
                                    print(f"Found asset field in detailed form: {field_name}")
                                    
                                    if 'relatedAsset' in relationship and 'data' in relationship['relatedAsset']:
                                        asset_data = relationship['relatedAsset']['data']
                                        asset_id = asset_data.get('id')
                                        
                                        if asset_id:
                                            print(f"Found related asset ID in detailed form: {asset_id}")
                                            
                                            # Check if we already have this asset
                                            if not any(ref.get('id') == asset_id for ref in references):
                                                asset_details = get_asset_details(asset_id, project_id, headers)
                                                if asset_details:
                                                    references.append({
                                                        'id': asset_id,
                                                        'name': asset_details.get('name', 'Unknown Asset'),
                                                        'description': asset_details.get('description', ''),
                                                        'type': 'form_relationship_field',
                                                        'match_reason': f'Found in detailed form relationship field: {field_name}',
                                                        'relationship_id': None,
                                                        'field_name': field_name
                                                    })
            
            # Check for references in the detailed form data
            if 'data' in detailed_form:
                form_data_detailed = detailed_form['data']
                print(f"Detailed form data keys: {list(form_data_detailed.keys())}")
                
                # Look for reference fields
                for key, value in form_data_detailed.items():
                    if 'reference' in key.lower() or 'related' in key.lower() or 'asset' in key.lower():
                        print(f"Found potential reference field '{key}': {value}")
                        if value:
                            references.extend(process_form_references(value, project_id, headers))
        else:
            print("Could not get detailed form data from any endpoint")
        
        # Try the new relationships:search endpoint (primary method)
        print("=== Using relationships:search endpoint ===")
        search_references = search_form_relationships(form_data, project_id, headers)
        references.extend(search_references)
        
        # If no relationships found via search, try the old method as fallback
        if not search_references:
            print("=== No relationships found via search, trying fallback methods ===")
            # Try the correct ACC Relationship Service API (as fallback)
            # First, we need to find relationships for this form
            # The project ID might be the container ID, or we might need to get it differently
            container_id = project_id  # Try using project ID as container ID
            
            # Try to search for relationships involving this form
            # We'll try different approaches to find relationships
            
            # Approach 1: Try to get all relationships for the container
            relationships_url = f'https://developer.api.autodesk.com/bim360/relationship/v2/containers/{container_id}/relationships'
            print(f"Trying to get all relationships from: {relationships_url}")
            
            rel_response = requests.get(relationships_url, headers=headers)
            print(f"Relationships response status: {rel_response.status_code}")
            
            if rel_response.ok:
                rel_data = rel_response.json()
                print(f"Found {len(rel_data.get('data', []))} relationships")
                
                # Look for relationships involving this form
                for relationship in rel_data.get('data', []):
                    relationship_id = relationship.get('id')
                    entities = relationship.get('entities', [])
                    for entity in entities:
                        # Check if this entity is our form (try both original ID and URN format)
                        entity_id = entity.get('id')
                        if entity_id == form_id or entity_id == form_entity.get('id') if form_entity else None:
                            print(f"Found relationship involving form: {relationship}")
                            # Get the other entity in the relationship
                            for other_entity in entities:
                                if other_entity.get('id') != entity_id:
                                    if other_entity.get('type') == 'asset':
                                        asset_info = extract_asset_from_relationship_entity(other_entity, project_id, headers, relationship_id)
                                        if asset_info:
                                            references.append(asset_info)
            else:
                print(f"Relationships request failed: {rel_response.status_code} - {rel_response.text}")
                
                # Approach 2: Try with different container ID format
                # Sometimes the container ID needs to be prefixed with 'b.'
                if not container_id.startswith('b.'):
                    alt_container_id = f'b.{container_id}'
                    alt_relationships_url = f'https://developer.api.autodesk.com/bim360/relationship/v2/containers/{alt_container_id}/relationships'
                    print(f"Trying alternative container ID: {alt_relationships_url}")
                    
                    alt_rel_response = requests.get(alt_relationships_url, headers=headers)
                    print(f"Alternative relationships response status: {alt_rel_response.status_code}")
                    
                    if alt_rel_response.ok:
                        alt_rel_data = alt_rel_response.json()
                        print(f"Found {len(alt_rel_data.get('data', []))} relationships with alt container ID")
                        
                        for relationship in alt_rel_data.get('data', []):
                            relationship_id = relationship.get('id')
                            entities = relationship.get('entities', [])
                            for entity in entities:
                                # Check if this entity is our form (try both original ID and URN format)
                                entity_id = entity.get('id')
                                if entity_id == form_id or entity_id == form_entity.get('id') if form_entity else None:
                                    print(f"Found relationship involving form: {relationship}")
                                    for other_entity in entities:
                                        if other_entity.get('id') != entity_id:
                                            if other_entity.get('type') == 'asset':
                                                asset_info = extract_asset_from_relationship_entity(other_entity, project_id, headers, relationship_id)
                                                if asset_info:
                                                    references.append(asset_info)
        
        print(f"=== Found {len(references)} references for form {form_id} ===")
        return references
        
    except Exception as e:
        print(f"Error getting form references: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def process_form_references(references_data, project_id, headers):
    """
    Process references data to extract asset information
    """
    assets = []
    
    try:
        if isinstance(references_data, dict):
            # Handle dictionary format
            for ref_type, ref_items in references_data.items():
                print(f"Processing reference type: {ref_type}")
                if isinstance(ref_items, list):
                    for item in ref_items:
                        if ref_type.lower() == 'assets' or 'asset' in ref_type.lower():
                            asset_info = extract_asset_from_reference(item, project_id, headers)
                            if asset_info:
                                assets.append(asset_info)
        
        elif isinstance(references_data, list):
            # Handle list format
            for item in references_data:
                if isinstance(item, dict):
                    # Check if this is an asset reference
                    if 'type' in item and item['type'] == 'asset':
                        asset_info = extract_asset_from_reference(item, project_id, headers)
                        if asset_info:
                            assets.append(asset_info)
                    elif 'assetId' in item or 'asset_id' in item:
                        asset_info = extract_asset_from_reference(item, project_id, headers)
                        if asset_info:
                            assets.append(asset_info)
        
        return assets
        
    except Exception as e:
        print(f"Error processing form references: {str(e)}")
        return []

def extract_asset_from_reference(reference_item, project_id, headers):
    """
    Extract asset information from a reference item
    """
    try:
        asset_id = None
        asset_name = None
        
        # Try different possible field names for asset ID
        if 'id' in reference_item:
            asset_id = reference_item['id']
        elif 'assetId' in reference_item:
            asset_id = reference_item['assetId']
        elif 'asset_id' in reference_item:
            asset_id = reference_item['asset_id']
        
        # Try different possible field names for asset name
        if 'name' in reference_item:
            asset_name = reference_item['name']
        elif 'assetName' in reference_item:
            asset_name = reference_item['assetName']
        elif 'title' in reference_item:
            asset_name = reference_item['title']
        
        if asset_id:
            # Get detailed asset information
            asset_details = get_asset_details(asset_id, project_id, headers)
            if asset_details:
                return {
                    'id': asset_id,
                    'name': asset_details.get('name', asset_name or 'Unknown Asset'),
                    'description': asset_details.get('description', ''),
                    'type': 'form_reference',
                    'match_reason': f'Direct reference in form data'
                }
            else:
                # Return basic info if we can't get details
                return {
                    'id': asset_id,
                    'name': asset_name or 'Unknown Asset',
                    'description': 'Asset details not available',
                    'type': 'form_reference',
                    'match_reason': f'Direct reference in form data (ID: {asset_id})'
                }
        
        return None
        
    except Exception as e:
        print(f"Error extracting asset from reference: {str(e)}")
        return None

@app.route('/relationships_debug')
def relationships_debug():
    """
    Debug page to show all possible relationships from ACC Relationship Service
    """
    if not is_authenticated():
        return redirect(url_for('login'))
    
    return render_template('relationships_debug.html')

@app.route('/api/relationships/debug')
def get_relationships_debug():
    """
    API endpoint to get all relationship information for debugging
    """
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        token = session.get('access_token')
        headers = get_autodesk_headers(token)
        
        debug_data = {
            'writable_relationships': [],
            'project_relationships': [],
            'form_entities': [],
            'asset_entities': [],
            'errors': []
        }
        
        # 1. Get writable relationships
        print("=== Getting Writable Relationships ===")
        try:
            writable_url = 'https://developer.api.autodesk.com/bim360/relationship/v2/utility/relationships:writable'
            writable_response = requests.get(writable_url, headers=headers)
            print(f"Writable relationships response: {writable_response.status_code}")
            
            if writable_response.ok:
                debug_data['writable_relationships'] = writable_response.json()
                print(f"Writable relationships: {debug_data['writable_relationships']}")
            else:
                debug_data['errors'].append(f"Writable relationships failed: {writable_response.status_code} - {writable_response.text}")
        except Exception as e:
            debug_data['errors'].append(f"Writable relationships error: {str(e)}")
        
        # 2. Get project relationships (try to get project ID from session or use a default)
        print("=== Getting Project Relationships ===")
        try:
            # Try to get the current project ID from session
            current_project = session.get('current_project_id')
            if not current_project:
                debug_data['errors'].append("No project ID available in session")
            else:
                # Try different container ID formats
                container_ids = [current_project, f'b.{current_project}']
                
                for container_id in container_ids:
                    try:
                        rel_url = f'https://developer.api.autodesk.com/bim360/relationship/v2/containers/{container_id}/relationships'
                        print(f"Trying container ID: {container_id}")
                        
                        rel_response = requests.get(rel_url, headers=headers)
                        print(f"Relationships response for {container_id}: {rel_response.status_code}")
                        
                        if rel_response.ok:
                            rel_data = rel_response.json()
                            debug_data['project_relationships'].append({
                                'container_id': container_id,
                                'relationships': rel_data.get('data', []),
                                'total_count': len(rel_data.get('data', []))
                            })
                            print(f"Found {len(rel_data.get('data', []))} relationships for {container_id}")
                            break  # Stop if we found relationships
                        else:
                            debug_data['errors'].append(f"Container {container_id} failed: {rel_response.status_code} - {rel_response.text}")
                    except Exception as e:
                        debug_data['errors'].append(f"Container {container_id} error: {str(e)}")
        except Exception as e:
            debug_data['errors'].append(f"Project relationships error: {str(e)}")
        
        # 3. Get some sample forms to check their entity types
        print("=== Getting Sample Forms ===")
        try:
            if current_project:
                forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{current_project}/forms'
                forms_response = requests.get(forms_url, headers=headers)
                
                if forms_response.ok:
                    forms_data = forms_response.json()
                    sample_forms = forms_data.get('data', [])[:3]  # Get first 3 forms
                    
                    for form in sample_forms:
                        form_entity = {
                            'form_id': form.get('id'),
                            'form_name': form.get('displayName', 'Unknown'),
                            'possible_urn': f'urn:adsk.wipprod:dm.lineage:{form.get("id")}',
                            'domain': 'autodesk-construction-forms',
                            'type': 'form'
                        }
                        debug_data['form_entities'].append(form_entity)
                else:
                    debug_data['errors'].append(f"Forms API failed: {forms_response.status_code} - {forms_response.text}")
        except Exception as e:
            debug_data['errors'].append(f"Sample forms error: {str(e)}")
        
        # 4. Get some sample assets
        print("=== Getting Sample Assets ===")
        try:
            if current_project:
                assets_url = f'https://developer.api.autodesk.com/construction/assets/v1/projects/{current_project}/assets'
                assets_response = requests.get(assets_url, headers=headers)
                
                if assets_response.ok:
                    assets_data = assets_response.json()
                    sample_assets = assets_data.get('data', [])[:3]  # Get first 3 assets
                    
                    for asset in sample_assets:
                        asset_entity = {
                            'asset_id': asset.get('id'),
                            'asset_name': asset.get('name', 'Unknown'),
                            'domain': 'autodesk-bim360-asset',
                            'type': 'asset'
                        }
                        debug_data['asset_entities'].append(asset_entity)
                else:
                    debug_data['errors'].append(f"Assets API failed: {assets_response.status_code} - {assets_response.text}")
        except Exception as e:
            debug_data['errors'].append(f"Sample assets error: {str(e)}")
        
        return jsonify(debug_data)
        
    except Exception as e:
        return jsonify({'error': f'Debug failed: {str(e)}'}), 500

def search_forms_by_name_pattern(forms_data, search_patterns):
    """
    Search for forms with names similar to the given patterns using fuzzy matching
    """
    import re
    
    matching_forms = []
    search_patterns = [pattern.lower() for pattern in search_patterns]
    
    for form in forms_data:
        form_name = form.get('name', '').lower()
        
        # Check for exact matches first
        for pattern in search_patterns:
            if pattern in form_name:
                matching_forms.append({
                    'form': form,
                    'match_type': 'exact',
                    'pattern': pattern
                })
                break
        
        # If no exact match, check for fuzzy matches
        if not any(pattern in form_name for pattern in search_patterns):
            for pattern in search_patterns:
                # Split pattern into words and check if most words are present
                pattern_words = pattern.split()
                form_words = form_name.split()
                
                # Check if at least 2 words from pattern are in form name
                matching_words = sum(1 for word in pattern_words if any(word in form_word for form_word in form_words))
                if matching_words >= 2:
                    matching_forms.append({
                        'form': form,
                        'match_type': 'fuzzy',
                        'pattern': pattern,
                        'matching_words': matching_words
                    })
                    break
    
    return matching_forms

def get_project_forms_api(project_id):
    """
    Get forms for a specific project with enhanced relationship detection
    """
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        token = session.get('access_token')
        headers = get_autodesk_headers(token)
        
        # Get forms from ACC
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms'
        print(f"Fetching forms from: {forms_url}")
        
        response = requests.get(forms_url, headers=headers)
        print(f"Forms response status: {response.status_code}")
        
        if not response.ok:
            print(f"Forms request failed: {response.status_code} - {response.text}")
            return jsonify({'error': f'Failed to fetch forms: {response.status_code}'}), response.status_code
        
        forms_data = response.json()
        print(f"Found {len(forms_data.get('data', []))} forms")
        
        # Search for extension of time related forms
        extension_patterns = [
            'extension of time',
            'extension_of_time', 
            'extension',
            'time extension',
            'eot',
            'extension request',
            'time request'
        ]
        
        extension_forms = search_forms_by_name_pattern(forms_data.get('data', []), extension_patterns)
        
        if extension_forms:
            print(f"=== Found {len(extension_forms)} extension-related forms ===")
            for match in extension_forms:
                form = match['form']
                print(f"Form: {form.get('name')} (Match: {match['match_type']}, Pattern: {match['pattern']})")
        else:
            print("=== No extension-related forms found ===")
        
        # Process all forms with relationship detection
        processed_forms = []
        forms_list = forms_data.get('data', [])
        
        for i, form in enumerate(forms_list):
            print(f"Processing form {i+1}: {form}")
            
            # Get asset relationships for this form
            assets = get_form_asset_relationships(form, project_id, headers)
            
            # Create processed form object
            processed_form = {
                'id': form.get('id'),
                'name': form.get('name'),
                'created_at': form.get('createdAt'),
                'status': form.get('status'),
                'assets': assets
            }
            
            processed_forms.append(processed_form)
            print(f"Successfully processed form: {processed_form}")
        
        return jsonify(processed_forms)
        
    except Exception as e:
        print(f"Error in get_project_forms_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/forms/<project_id>/search-extension')
def search_extension_forms(project_id):
    """
    Search for forms related to extension of time in a specific project
    """
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        token = session.get('access_token')
        headers = get_autodesk_headers(token)
        
        # Get forms from ACC
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms'
        print(f"Searching for extension forms in: {forms_url}")
        
        response = requests.get(forms_url, headers=headers)
        print(f"Forms response status: {response.status_code}")
        
        if not response.ok:
            print(f"Forms request failed: {response.status_code} - {response.text}")
            return jsonify({'error': f'Failed to fetch forms: {response.status_code}'}), response.status_code
        
        forms_data = response.json()
        print(f"Found {len(forms_data.get('data', []))} total forms")
        
        # Search for extension of time related forms
        extension_patterns = [
            'extension of time',
            'extension_of_time', 
            'extension',
            'time extension',
            'eot',
            'extension request',
            'time request',
            'delay',
            'time delay',
            'schedule extension',
            'contract extension'
        ]
        
        extension_forms = search_forms_by_name_pattern(forms_data.get('data', []), extension_patterns)
        
        # Process extension forms with relationship detection
        processed_extension_forms = []
        
        for match in extension_forms:
            form = match['form']
            print(f"Processing extension form: {form.get('name')}")
            
            # Get asset relationships for this form
            assets = get_form_asset_relationships(form, project_id, headers)
            
            # Create processed form object
            processed_form = {
                'id': form.get('id'),
                'name': form.get('name'),
                'created_at': form.get('createdAt'),
                'status': form.get('status'),
                'assets': assets,
                'match_info': {
                    'type': match['match_type'],
                    'pattern': match['pattern'],
                    'matching_words': match.get('matching_words', 0)
                }
            }
            
            processed_extension_forms.append(processed_form)
            print(f"Successfully processed extension form: {processed_form}")
        
        result = {
            'total_forms_found': len(forms_data.get('data', [])),
            'extension_forms_found': len(extension_forms),
            'extension_forms': processed_extension_forms,
            'search_patterns_used': extension_patterns
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in search_extension_forms: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/forms/<project_id>/quick-extension-search')
def quick_extension_search(project_id):
    """
    Quick search for extension of time claim forms without processing all forms
    """
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        token = session.get('access_token')
        headers = get_autodesk_headers(token)
        
        # Get forms from ACC
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms'
        print(f"Quick search for extension forms in: {forms_url}")
        
        response = requests.get(forms_url, headers=headers)
        print(f"Forms response status: {response.status_code}")
        
        if not response.ok:
            print(f"Forms request failed: {response.status_code} - {response.text}")
            return jsonify({'error': f'Failed to fetch forms: {response.status_code}'}), response.status_code
        
        forms_data = response.json()
        all_forms = forms_data.get('data', [])
        print(f"Found {len(all_forms)} total forms")
        
        # Quick search for extension of time claim forms
        extension_forms = []
        search_terms = ['extension of time claim', 'extension_of_time_claim', 'eot claim', 'time claim']
        
        for form in all_forms:
            form_name = form.get('name', '').lower()
            if any(term in form_name for term in search_terms):
                extension_forms.append({
                    'id': form.get('id'),
                    'name': form.get('name'),
                    'created_at': form.get('createdAt'),
                    'status': form.get('status'),
                    'form_num': form.get('formNum'),
                    'form_date': form.get('formDate'),
                    'assets': [],  # Will be populated on-demand
                    'relationships_checked': False
                })
                print(f"Found extension form: {form.get('name')}")
        
        result = {
            'total_forms_found': len(all_forms),
            'extension_forms_found': len(extension_forms),
            'extension_forms': extension_forms,
            'search_terms_used': search_terms
        }
        
        print(f"Quick search complete: {len(extension_forms)} extension forms found")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in quick_extension_search: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/forms/<form_id>/generate-relationships', methods=['POST'])
def generate_form_relationships(form_id):
    """
    Generate relationships for a specific form on-demand
    """
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        token = session.get('access_token')
        headers = get_autodesk_headers(token)
        
        # Get project_id from request
        project_id = request.json.get('project_id')
        if not project_id:
            return jsonify({'error': 'Project ID required'}), 400
        
        print(f"Generating relationships for form: {form_id} in project: {project_id}")
        
        # Get the specific form data
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms'
        response = requests.get(forms_url, headers=headers)
        
        if not response.ok:
            return jsonify({'error': f'Failed to fetch forms: {response.status_code}'}), response.status_code
        
        forms_data = response.json()
        all_forms = forms_data.get('data', [])
        
        # Find the specific form
        target_form = None
        for form in all_forms:
            if form.get('id') == form_id:
                target_form = form
                break
        
        if not target_form:
            return jsonify({'error': f'Form {form_id} not found'}), 404
        
        print(f"Found target form: {target_form.get('name')}")
        
        # Generate relationships for this specific form
        assets = get_form_asset_relationships(target_form, project_id, headers)
        
        result = {
            'form_id': form_id,
            'form_name': target_form.get('name'),
            'assets': assets,
            'relationships_checked': True
        }
        
        print(f"Generated relationships for {target_form.get('name')}: {len(assets)} assets found")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in generate_form_relationships: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/quick_extension_test')
def quick_extension_test():
    """
    Quick test page for extension of time claim forms
    """
    if not is_authenticated():
        return redirect(url_for('login'))
    
    return render_template('quick_extension_test.html')

@app.route('/extension_forms_relationships')
def extension_forms_relationships():
    """Show Extension of Time Claim forms with their asset relationships"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    return render_template('extension_forms_relationships.html')

@app.route('/form_exporter')
def form_exporter():
    """Advanced form exporter with relationships and automatic PDF export"""
    if 'access_token' not in session:
        return redirect(url_for('index'))
    
    hub_id = request.args.get('hub_id')
    if not hub_id:
        return redirect(url_for('select_hub'))
    
    # Store the selected hub_id in the session
    session['selected_hub_id'] = hub_id
    
    # Get hub details to extract region and name
    headers = {
        'Authorization': f'Bearer {session["access_token"]}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get hub details to extract region and name
        hub_response = requests.get(
            f'https://developer.api.autodesk.com/project/v1/hubs/{hub_id}',
            headers=headers
        )
        hub_response.raise_for_status()
        hub_data = hub_response.json()
        hub_region = hub_data['data']['attributes'].get('region', 'US')
        hub_name = hub_data['data']['attributes'].get('name', 'Unknown Hub')
        
        return render_template('form_exporter.html', hub_region=hub_region, hub_name=hub_name)
    except Exception as e:
        print(f"Error fetching hub details: {str(e)}")
        flash(f'Error fetching hub details: {str(e)}', 'error')
        return redirect(url_for('select_hub'))

@app.route('/api/extension_forms_relationships/<project_id>')
def get_extension_forms_relationships(project_id):
    """Get Extension of Time Claim forms with their asset relationships"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        headers = get_autodesk_headers(session['access_token'])
        
        # Get all forms for the project
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms'
        print(f"Fetching forms from: {forms_url}")
        
        forms_response = requests.get(forms_url, headers=headers)
        if not forms_response.ok:
            print(f"Forms request failed: {forms_response.status_code}")
            return jsonify({'error': f'Failed to fetch forms: {forms_response.status_code}'}), 500
        
        forms_data = forms_response.json()
        all_forms = forms_data.get('data', [])
        print(f"Total forms found: {len(all_forms)}")
        
        # Filter for Extension of Time Claim forms
        extension_forms = []
        search_patterns = ['extension of time claim', 'extension of time', 'time claim', 'extension claim']
        
        for form in all_forms:
            form_name = form.get('name', '').lower()
            if any(pattern in form_name for pattern in search_patterns):
                extension_forms.append(form)
        
        print(f"Extension forms found: {len(extension_forms)}")
        
        # Get relationships for each extension form
        forms_with_relationships = []
        
        for form in extension_forms:
            form_id = form.get('id')
            form_name = form.get('name', 'Unknown Form')
            
            print(f"Processing form: {form_name} (ID: {form_id})")
            
            # Get relationships for this form
            related_assets = search_form_relationships(form, project_id, headers)
            
            forms_with_relationships.append({
                'form_id': form_id,
                'form_name': form_name,
                'form_created': form.get('createdAt', ''),
                'related_assets': related_assets,
                'relationship_count': len(related_assets)
            })
        
        return jsonify({
            'forms': forms_with_relationships,
            'total_forms': len(forms_with_relationships)
        })
        
    except Exception as e:
        print(f"Error getting extension forms relationships: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/form_exporter/<project_id>')
def get_form_exporter_data(project_id):
    """Get all forms with relationships for a project using optimized processing with SQLite caching"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        headers = get_autodesk_headers(session['access_token'])
        clean_project_id = project_id[2:] if project_id.startswith('b.') else project_id
        
        print(f"🚀 Starting optimized form processing for project: {clean_project_id}")
        
        # Initialize progress tracking
        global current_progress
        current_progress = {
            'percentage': 0,
            'message': 'Starting form processing...',
            'current': 0,
            'total': 0,
            'project_id': clean_project_id
        }
        
        # Check cache size before proceeding
        check_cache_size()
        
        # Clean up old entries periodically
        cleanup_old_cache_entries()
        
        # Step 1: Check SQLite cache for forms data
        print("📋 Step 1: Checking forms cache...")
        cached_forms_data = None
        try:
            conn = sqlite3.connect(CACHE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT forms_data FROM forms_cache 
                WHERE project_id = ?
            ''', (clean_project_id,))
            
            result = cursor.fetchone()
            if result:
                cached_forms_data = json.loads(result[0])
                print(f"✅ Using cached forms data for project: {clean_project_id}")
                
                # Update last accessed timestamp
                cursor.execute('''
                    UPDATE forms_cache 
                    SET last_accessed = CURRENT_TIMESTAMP 
                    WHERE project_id = ?
                ''', (clean_project_id,))
                conn.commit()
            else:
                print(f"📥 No cached forms data found for project: {clean_project_id}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error checking forms cache: {e}")
        
        # Step 2: Fetch forms data if not cached
        if not cached_forms_data:
            print("📥 Fetching forms data from API...")
            url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{clean_project_id}/forms'
            forms_response = requests.get(url, headers=headers)
            if not forms_response.ok:
                return jsonify({'error': f'Failed to fetch forms: {forms_response.status_code}'}), 500
            
            cached_forms_data = forms_response.json()
            
            # Cache the forms data in SQLite
            try:
                conn = sqlite3.connect(CACHE_FILE)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO forms_cache (project_id, forms_data, created_at, last_accessed)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (clean_project_id, json.dumps(cached_forms_data)))
                
                conn.commit()
                conn.close()
                print(f"💾 Cached forms data for project: {clean_project_id}")
                
            except Exception as e:
                print(f"⚠️ Error caching forms data: {e}")
        
        all_forms = cached_forms_data.get('data', [])
        print(f"✅ Found {len(all_forms)} total forms")
        
        # Step 3: Pre-fetch all locations for the project (cached)
        print("🌍 Step 3: Pre-fetching all locations...")
        location_lookup = get_all_locations_for_project(clean_project_id, headers)
        print(f"✅ Cached {len(location_lookup)} locations")
        
        # Step 4: Get all relationships for the project (ONCE)
        print("🔗 Step 4: Fetching all relationships for the project...")
        all_relationships = search_project_relationships(clean_project_id, headers)
        print(f"✅ Found {len(all_relationships)} total relationships for project")
        
        # Step 5: Process all forms with relationships (using the single relationships dataset)
        print("📋 Step 5: Processing forms with relationships...")
        forms_with_relationships = []
        total_relationships = 0
        total_assets = 0
        
        for i, form in enumerate(all_forms):
            form_id = form.get('id')
            form_name = form.get('name', 'Unknown Form')
            
            # Show progress every 5 forms
            if i % 5 == 0:
                progress = (i / len(all_forms)) * 100
                print(f"📊 Progress: {progress:.1f}% ({i}/{len(all_forms)}) - Processing: {form_name}")
                
                # Update global progress for frontend polling
                current_progress = {
                    'percentage': round(progress),
                    'message': f"Processing form {i+1} of {len(all_forms)}: {form_name}",
                    'current': i+1,
                    'total': len(all_forms),
                    'project_id': clean_project_id
                }
                print(f"🔄 Updated progress: {round(progress)}% - {form_name}")
                
                # Small delay to ensure progress is visible
                import time
                time.sleep(0.1)
            
            # Find relationships for this form from the already-fetched relationships
            form_relationships = []
            
            # Look through all relationships to find ones that include this form
            for relationship in all_relationships:
                entities = relationship.get('entities', [])
                
                # Check if this form is involved in this relationship
                form_involved = False
                other_entities = []
                
                for entity in entities:
                    entity_type = entity.get('type')
                    entity_id = entity.get('id')
                    
                    # Clean the entity ID if it has URN prefix
                    clean_entity_id = entity_id
                    if entity_id.startswith('urn:adsk.wipprod:dm.lineage:'):
                        clean_entity_id = entity_id.split(':')[-1]
                    
                    if entity_type == 'form' and clean_entity_id == form_id:
                        form_involved = True
                    elif entity_type == 'asset':
                        # Get asset details
                        asset_details = get_asset_details(clean_entity_id, clean_project_id, headers)
                        if asset_details:
                            # Get location details using cached data
                            location_id = asset_details.get('locationId', '')
                            location_details = location_lookup.get(location_id, {})
                            
                            other_entities.append({
                                'id': clean_entity_id,
                                'name': asset_details.get('name', 'Unknown Asset'),
                                'description': asset_details.get('description', ''),
                                'clientAssetId': asset_details.get('clientAssetId', ''),
                                'locationId': asset_details.get('locationId', ''),
                                'locationName': location_details.get('name', 'N/A'),
                                'barcode': asset_details.get('barcode', ''),
                                'type': 'asset',
                                'relationship_id': relationship.get('id')
                            })
                
                if form_involved and other_entities:
                    form_relationships.extend(other_entities)
            
            # Enhance assets with location names using cached data
            for asset in form_relationships:
                if asset.get('locationId'):
                    location_details = location_lookup.get(asset['locationId'], {})
                    asset['locationName'] = location_details.get('name', f'Location {asset["locationId"]}')
                else:
                    asset['locationName'] = 'N/A'
            
            # Always add the form, regardless of whether it has relationships
            forms_with_relationships.append({
                'form_id': form.get('id'),
                'form_name': form_name,
                'form_date': form.get('formDate', ''),  # Use formDate from ACC API
                'form_created': form.get('createdAt', ''),  # Keep created date for reference
                'relationship_id': form.get('relationship_id'),
                'related_assets': form_relationships
            })
            
            total_relationships += len(form_relationships)
            total_assets += len(form_relationships)
        
        print(f"✅ Found {len(forms_with_relationships)} forms with relationships")
        print(f"📊 Total relationships: {total_relationships}")
        print(f"🏗️ Total assets: {total_assets}")
        
        # Set progress to 100% when processing is complete
        current_progress = {
            'percentage': 100,
            'message': f'Processing Complete - Found {len(forms_with_relationships)} forms with relationships',
            'current': len(all_forms),
            'total': len(all_forms),
            'project_id': clean_project_id
        }
        print(f"🎉 Processing complete! Progress set to 100%")
        
        return jsonify({
            'forms': forms_with_relationships,
            'total_forms': len(all_forms),
            'forms_with_relationships': len(forms_with_relationships),
            'total_relationships': total_relationships,
            'total_assets': total_assets
        })
        
    except Exception as e:
        print(f"💥 Error in get_form_exporter_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/progress/<project_id>')
def get_progress(project_id):
    """Get current progress for a project"""
    global current_progress
    
    # Clean the project ID to match the backend format
    clean_project_id = project_id[2:] if project_id.startswith('b.') else project_id
    
    print(f"🔍 Progress request for project: {project_id} (cleaned: {clean_project_id})")
    print(f"🔍 Current progress project: {current_progress['project_id']}")
    print(f"🔍 Current progress data: {current_progress}")
    
    if current_progress['project_id'] == clean_project_id:
        print(f"✅ Returning progress: {current_progress['percentage']}%")
        return jsonify(current_progress)
    else:
        print(f"❌ Project ID mismatch, returning no progress")
        return jsonify({'percentage': 0, 'message': 'No progress available'})

@app.route('/api/form_exporter_progress/<project_id>')
def get_form_exporter_progress(project_id):
    """Stream progress updates for form processing"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get the access token before entering the generator
    access_token = session['access_token']
    
    def generate():
        try:
            headers = get_autodesk_headers(access_token)
            clean_project_id = project_id[2:] if project_id.startswith('b.') else project_id
            
            print(f"🚀 Starting progress stream for project: {clean_project_id}")
            
            # Step 1: Check cache (10%)
            yield f"data: {json.dumps({'progress': 10, 'message': 'Checking cache for existing data...', 'stage': 1})}\n\n"
            
            # Check SQLite cache for forms data
            cached_forms_data = None
            try:
                conn = sqlite3.connect(CACHE_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT forms_data FROM forms_cache WHERE project_id = ?', (clean_project_id,))
                result = cursor.fetchone()
                if result:
                    cached_forms_data = json.loads(result[0])
                conn.close()
            except Exception as e:
                print(f"⚠️ Error checking forms cache: {e}")
            
            # Step 2: Fetch forms if not cached (20%)
            yield f"data: {json.dumps({'progress': 20, 'message': 'Fetching forms from ACC API...', 'stage': 2})}\n\n"
            
            if not cached_forms_data:
                url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{clean_project_id}/forms'
                forms_response = requests.get(url, headers=headers)
                if not forms_response.ok:
                    yield f"data: {json.dumps({'error': f'Failed to fetch forms: {forms_response.status_code}'})}\n\n"
                    return
                cached_forms_data = forms_response.json()
            
            # Step 3: Load locations (30%)
            yield f"data: {json.dumps({'progress': 30, 'message': 'Loading location information...', 'stage': 3})}\n\n"
            location_lookup = get_all_locations_for_project(clean_project_id, headers)
            
            # Step 4: Get relationships (40%)
            yield f"data: {json.dumps({'progress': 40, 'message': 'Finding form relationships...', 'stage': 4})}\n\n"
            all_relationships = search_project_relationships(clean_project_id, headers)
            
            # Step 5: Process forms (50-100%)
            yield f"data: {json.dumps({'progress': 50, 'message': 'Processing forms and analyzing relationships...', 'stage': 5})}\n\n"
            
            all_forms = cached_forms_data.get('data', [])
            forms_with_relationships = []
            
            for i, form in enumerate(all_forms):
                # Calculate real progress based on form processing
                progress = 50 + (i / len(all_forms)) * 45  # 50% to 95%
                message = f"Processing form {i+1} of {len(all_forms)}: {form.get('name', 'Unknown Form')}"
                
                yield f"data: {json.dumps({'progress': round(progress), 'message': message, 'stage': 5})}\n\n"
                
                # Process the form (simplified for progress streaming)
                form_id = form.get('id')
                form_relationships = []
                
                # Find relationships for this form
                for relationship in all_relationships:
                    entities = relationship.get('entities', [])
                    form_involved = False
                    other_entities = []
                    
                    for entity in entities:
                        entity_type = entity.get('type')
                        entity_id = entity.get('id')
                        clean_entity_id = entity_id.split(':')[-1] if entity_id.startswith('urn:adsk.wipprod:dm.lineage:') else entity_id
                        
                        if entity_type == 'form' and clean_entity_id == form_id:
                            form_involved = True
                        elif entity_type == 'asset':
                            asset_details = get_asset_details(clean_entity_id, clean_project_id, headers)
                            if asset_details:
                                location_id = asset_details.get('locationId', '')
                                location_details = location_lookup.get(location_id, {})
                                other_entities.append({
                                    'id': clean_entity_id,
                                    'name': asset_details.get('name', 'Unknown Asset'),
                                    'locationName': location_details.get('name', 'N/A'),
                                    'barcode': asset_details.get('barcode', ''),
                                    'relationship_id': relationship.get('id')
                                })
                    
                    if form_involved and other_entities:
                        form_relationships.extend(other_entities)
                
                forms_with_relationships.append({
                    'form_id': form.get('id'),
                    'form_name': form.get('name', 'Unknown Form'),
                    'form_date': form.get('formDate', ''),
                    'related_assets': form_relationships
                })
            
            # Step 6: Complete (100%)
            yield f"data: {json.dumps({'progress': 100, 'message': 'Finalizing data preparation...', 'stage': 6, 'complete': True})}\n\n"
            
        except Exception as e:
            print(f"💥 Error in progress stream: {str(e)}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/plain')
    """Get all forms with relationships for a project using optimized processing with SQLite caching"""


@app.route('/api/forms/<project_id>/relationships')
def get_project_forms_with_relationships(project_id):
    """Get all forms with detailed relationships for the form downloader"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        headers = get_autodesk_headers(session['access_token'])
        
        print(f"=== Getting forms with relationships for project: {project_id} ===")
        
        # Clean project ID
        clean_project_id = project_id.replace('b.', '')
        
        # Get all forms for the project
        forms_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{clean_project_id}/forms'
        print(f"Fetching forms from: {forms_url}")
        
        forms_response = requests.get(forms_url, headers=headers)
        if not forms_response.ok:
            print(f"Forms request failed: {forms_response.status_code}")
            return jsonify({'error': f'Failed to fetch forms: {forms_response.status_code}'}), 500
        
        forms_data = forms_response.json()
        all_forms = forms_data.get('data', [])
        print(f"Total forms found: {len(all_forms)}")
        
        # Process all forms with relationships
        forms_with_relationships = []
        
        for form in all_forms:
            form_name = form.get('name', 'Unknown Form')
            form_id = form.get('id')
            form_created = form.get('createdAt', '')
            form_status = form.get('status', 'unknown')
            
            print(f"Processing form: {form_name} (ID: {form_id})")
            
            # Get detailed relationships for this form
            related_assets = find_relationships_for_form(form_id, clean_project_id, headers)
            
            # Convert to the format expected by the frontend
            formatted_assets = []
            for asset in related_assets:
                formatted_assets.append({
                    'id': asset.get('id'),
                    'name': asset.get('name', 'Unknown Asset'),
                    'clientAssetId': asset.get('clientAssetId', ''),
                    'locationId': asset.get('locationId', ''),
                    'locationName': asset.get('locationName', 'N/A'),
                    'barcode': asset.get('barcode', ''),
                    'description': asset.get('description', ''),
                    'relationship_id': asset.get('relationship_id', 'N/A')
                })
            
            # Create form info with relationships
            form_info = {
                'id': form_id,
                'name': form_name,
                'created_at': form_created,
                'status': form_status,
                'assets': [],  # Keep empty for backward compatibility
                'related_assets': formatted_assets  # Add detailed relationship data
            }
            
            forms_with_relationships.append(form_info)
            print(f"Added form {form_name} with {len(formatted_assets)} relationships")
        
        print(f"Processed {len(forms_with_relationships)} forms with relationships")
        
        return jsonify(forms_with_relationships)
        
    except Exception as e:
        print(f"Error getting forms with relationships: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500

def search_project_relationships(project_id, headers):
    """Get all relationships for a project (from project_relationships.py)"""
    try:
        print(f"=== Searching all relationships for project: {project_id} ===")
        
        # Remove any 'b.' prefix from project_id for the relationship API
        clean_project_id = project_id.replace('b.', '')
        print(f"Using clean project ID: {clean_project_id}")
        
        # Search for all relationships
        search_url = f'https://developer.api.autodesk.com/bim360/relationship/v2/containers/{clean_project_id}/relationships:search'
        
        # Search parameters to get all relationships
        params = {
            'pageLimit': 200  # Get more relationships
        }
        
        print(f"Searching relationships with URL: {search_url}")
        
        response = requests.get(search_url, headers=headers, params=params)
        print(f"Relationship search response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            relationships = data.get('relationships', [])
            print(f"Found {len(relationships)} total relationships for project {clean_project_id}")
            return relationships
        else:
            print(f"Relationship search failed: {response.status_code} - {response.text}")
            return []
        
    except Exception as e:
        print(f"Error searching project relationships: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_form_details(form_id, project_id, headers):
    """Get detailed form information"""
    try:
        # Clean the form ID if it has the urn prefix
        clean_form_id = form_id
        if form_id.startswith('urn:adsk.wipprod:dm.lineage:'):
            clean_form_id = form_id.split(':')[-1]
        
        print(f"Getting form details for: {clean_form_id}")
        
        # Try to get form details from the forms API
        form_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms/{clean_form_id}'
        response = requests.get(form_url, headers=headers)
        
        if response.ok:
            form_data = response.json()
            return {
                'name': form_data.get('name', 'Unknown Form'),
                'createdAt': form_data.get('createdAt', ''),
                'status': form_data.get('status', ''),
                'id': clean_form_id
            }
        else:
            print(f"Form details request failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting form details: {str(e)}")
        return None

# Global cache for locations to avoid repeated API calls
location_cache = {}

# Cache configuration
CACHE_FILE = 'cache.db'
CACHE_SIZE_THRESHOLD = 100 * 1024 * 1024  # 100 MB threshold (increased from 50 MB)
CACHE_CLEANUP_DAYS = 30  # Remove entries older than 30 days
CACHE_MAX_PROJECTS = 500  # Maximum number of cached projects

# Global progress tracking
current_progress = {
    'percentage': 0,
    'message': '',
    'current': 0,
    'total': 0,
    'project_id': None
}

def get_cache_file_size():
    """Get the size of the cache file in bytes"""
    try:
        if os.path.exists(CACHE_FILE):
            return os.path.getsize(CACHE_FILE)
        return 0
    except Exception as e:
        print(f"Error getting cache file size: {e}")
        return 0

def clear_cache_file():
    """Remove the cache file and create a new empty one"""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"🗑️ Removed cache file: {CACHE_FILE}")
        
        # Create new empty cache file
        init_cache_database()
        print(f"🆕 Created new cache file: {CACHE_FILE}")
        
        # Clear in-memory cache
        global location_cache
        location_cache = {}
        
    except Exception as e:
        print(f"Error clearing cache file: {e}")

def check_cache_size():
    """Check if cache file exceeds threshold and clear if needed"""
    cache_size = get_cache_file_size()
    
    if cache_size > CACHE_SIZE_THRESHOLD:
        print(f"⚠️ Cache file size ({cache_size / 1024 / 1024:.1f} MB) exceeds threshold ({CACHE_SIZE_THRESHOLD / 1024 / 1024:.1f} MB)")
        clear_cache_file()
        return True
    else:
        print(f"📊 Cache file size: {cache_size / 1024 / 1024:.1f} MB (threshold: {CACHE_SIZE_THRESHOLD / 1024 / 1024:.1f} MB)")
        return False

def init_cache_database():
    """Initialize the SQLite cache database with tables"""
    try:
        conn = sqlite3.connect(CACHE_FILE)
        cursor = conn.cursor()
        
        # Create locations cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_cache (
                project_id TEXT PRIMARY KEY,
                location_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create forms cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forms_cache (
                project_id TEXT PRIMARY KEY,
                forms_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create relationships cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships_cache (
                project_id TEXT PRIMARY KEY,
                relationships_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location_cache_last_accessed ON location_cache(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forms_cache_last_accessed ON forms_cache(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_cache_last_accessed ON relationships_cache(last_accessed)')
        
        conn.commit()
        conn.close()
        print(f"✅ Initialized cache database: {CACHE_FILE}")
        
    except Exception as e:
        print(f"Error initializing cache database: {e}")

def cleanup_old_cache_entries():
    """Remove cache entries older than the specified days and limit total projects"""
    try:
        conn = sqlite3.connect(CACHE_FILE)
        cursor = conn.cursor()
        
        # Get current cache statistics
        cursor.execute('SELECT COUNT(*) FROM location_cache')
        location_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM forms_cache')
        forms_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM relationships_cache')
        relationships_count = cursor.fetchone()[0]
        
        print(f"📊 Cache statistics before cleanup:")
        print(f"   - Location cache entries: {location_count}")
        print(f"   - Forms cache entries: {forms_count}")
        print(f"   - Relationships cache entries: {relationships_count}")
        
        # Step 1: Clean up old entries (older than 30 days)
        cutoff_date = datetime.now() - timedelta(days=CACHE_CLEANUP_DAYS)
        
        # Clean up old location cache entries
        cursor.execute('''
            DELETE FROM location_cache 
            WHERE last_accessed < ?
        ''', (cutoff_date,))
        location_deleted = cursor.rowcount
        
        # Clean up old forms cache entries
        cursor.execute('''
            DELETE FROM forms_cache 
            WHERE last_accessed < ?
        ''', (cutoff_date,))
        forms_deleted = cursor.rowcount
        
        # Clean up old relationships cache entries
        cursor.execute('''
            DELETE FROM relationships_cache 
            WHERE last_accessed < ?
        ''', (cutoff_date,))
        relationships_deleted = cursor.rowcount
        
        # Step 2: Limit to maximum 500 projects (keep most recently accessed)
        if location_count - location_deleted > CACHE_MAX_PROJECTS:
            # Keep only the 500 most recently accessed location entries
            cursor.execute('''
                DELETE FROM location_cache 
                WHERE project_id NOT IN (
                    SELECT project_id FROM location_cache 
                    ORDER BY last_accessed DESC 
                    LIMIT ?
                )
            ''', (CACHE_MAX_PROJECTS,))
            location_limit_deleted = cursor.rowcount
            print(f"   - Removed {location_limit_deleted} location entries to stay under {CACHE_MAX_PROJECTS} projects")
        else:
            location_limit_deleted = 0
        
        if forms_count - forms_deleted > CACHE_MAX_PROJECTS:
            # Keep only the 500 most recently accessed forms entries
            cursor.execute('''
                DELETE FROM forms_cache 
                WHERE project_id NOT IN (
                    SELECT project_id FROM forms_cache 
                    ORDER BY last_accessed DESC 
                    LIMIT ?
                )
            ''', (CACHE_MAX_PROJECTS,))
            forms_limit_deleted = cursor.rowcount
            print(f"   - Removed {forms_limit_deleted} forms entries to stay under {CACHE_MAX_PROJECTS} projects")
        else:
            forms_limit_deleted = 0
        
        if relationships_count - relationships_deleted > CACHE_MAX_PROJECTS:
            # Keep only the 500 most recently accessed relationships entries
            cursor.execute('''
                DELETE FROM relationships_cache 
                WHERE project_id NOT IN (
                    SELECT project_id FROM relationships_cache 
                    ORDER BY last_accessed DESC 
                    LIMIT ?
                )
            ''', (CACHE_MAX_PROJECTS,))
            relationships_limit_deleted = cursor.rowcount
            print(f"   - Removed {relationships_limit_deleted} relationships entries to stay under {CACHE_MAX_PROJECTS} projects")
        else:
            relationships_limit_deleted = 0
        
        # Get final statistics
        cursor.execute('SELECT COUNT(*) FROM location_cache')
        final_location_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM forms_cache')
        final_forms_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM relationships_cache')
        final_relationships_count = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        # Log cleanup results
        total_location_deleted = location_deleted + location_limit_deleted
        total_forms_deleted = forms_deleted + forms_limit_deleted
        total_relationships_deleted = relationships_deleted + relationships_limit_deleted
        
        if total_location_deleted > 0 or total_forms_deleted > 0 or total_relationships_deleted > 0:
            print(f"🧹 Cache cleanup completed:")
            print(f"   - Removed {location_deleted} old location entries (> {CACHE_CLEANUP_DAYS} days)")
            print(f"   - Removed {forms_deleted} old forms entries (> {CACHE_CLEANUP_DAYS} days)")
            print(f"   - Removed {relationships_deleted} old relationships entries (> {CACHE_CLEANUP_DAYS} days)")
            print(f"   - Removed {location_limit_deleted} location entries (over {CACHE_MAX_PROJECTS} limit)")
            print(f"   - Removed {forms_limit_deleted} forms entries (over {CACHE_MAX_PROJECTS} limit)")
            print(f"   - Removed {relationships_limit_deleted} relationships entries (over {CACHE_MAX_PROJECTS} limit)")
            print(f"   - Final cache: {final_location_count} location entries, {final_forms_count} forms entries, {final_relationships_count} relationships entries")
        else:
            print(f"✅ Cache is within limits: {final_location_count} location entries, {final_forms_count} forms entries, {final_relationships_count} relationships entries")
        
    except Exception as e:
        print(f"Error cleaning up old cache entries: {e}")

def get_all_locations_for_project(project_id, headers):
    """Get all locations for a project once and cache them with SQLite"""
    global location_cache
    
    # Check cache size before proceeding
    check_cache_size()
    
    # Clean up old entries periodically
    cleanup_old_cache_entries()
    
    # Clean project ID
    clean_project_id = project_id.replace('b.', '') if project_id.startswith('b.') else project_id
    
    # Check if we already have locations cached for this project
    if clean_project_id in location_cache:
        print(f"📋 Using in-memory cached locations for project: {clean_project_id}")
        return location_cache[clean_project_id]
    
    # Check SQLite cache
    try:
        conn = sqlite3.connect(CACHE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT location_data FROM location_cache 
            WHERE project_id = ?
        ''', (clean_project_id,))
        
        result = cursor.fetchone()
        if result:
            # Update last accessed time
            cursor.execute('''
                UPDATE location_cache 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE project_id = ?
            ''', (clean_project_id,))
            conn.commit()
            
            # Parse cached data
            location_lookup = json.loads(result[0])
            location_cache[clean_project_id] = location_lookup
            print(f"📋 Using SQLite cached locations for project: {clean_project_id}")
            conn.close()
            return location_lookup
            
        conn.close()
        
    except Exception as e:
        print(f"Error reading from SQLite cache: {e}")
    
    print(f"🌐 Fetching all locations for project: {clean_project_id}")
    
    try:
        # Use the BIM360 locations v2 API
        url = f'https://developer.api.autodesk.com/bim360/locations/v2/containers/{clean_project_id}/trees/default/nodes'
        response = requests.get(url, headers=headers)
        
        if response.ok:
            locations_data = response.json()
            locations = locations_data.get('results', [])
            print(f"📊 Found {len(locations)} locations for project {clean_project_id}")
            
            # Create a lookup dictionary for fast access
            location_lookup = {}
            for location in locations:
                location_id = location.get('id')
                if location_id:
                    location_lookup[location_id] = {
                        'name': location.get('name', 'Unknown Location'),
                        'id': location_id,
                        'description': location.get('description', ''),
                        'parentId': location.get('parentId', ''),
                        'type': location.get('type', ''),
                        'barcode': location.get('barcode', '')
                    }
            
            # Cache the locations in memory
            location_cache[clean_project_id] = location_lookup
            
            # Cache the locations in SQLite
            try:
                conn = sqlite3.connect(CACHE_FILE)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO location_cache (project_id, location_data, last_accessed)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (clean_project_id, json.dumps(location_lookup)))
                
                conn.commit()
                conn.close()
                print(f"✅ Cached {len(location_lookup)} locations for project {clean_project_id}")
                
            except Exception as e:
                print(f"Error writing to SQLite cache: {e}")
            
            return location_lookup
        else:
            print(f"❌ Failed to fetch locations: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"💥 Error fetching locations: {str(e)}")
        return {}

def get_location_details_fast(location_id, project_id, headers):
    """Get location details using cached data for faster performance"""
    if not location_id or location_id == 'N/A':
        return {'name': 'N/A', 'id': 'N/A'}
    
    # Get all locations for the project (cached)
    location_lookup = get_all_locations_for_project(project_id, headers)
    
    # Look up the specific location
    if location_id in location_lookup:
        return location_lookup[location_id]
    else:
        # If not found, return the ID as name
        return {'name': f'Location {location_id}', 'id': location_id}

def get_location_details(location_id, project_id, headers):
    """Get location details from location ID using BIM360 Locations v2 API"""
    # Use the fast version instead
    return get_location_details_fast(location_id, project_id, headers)

def analyze_form_content_for_relationships(form_data, project_id, headers):
    """Analyze form content to find asset relationships using the working logic"""
    try:
        form_id = form_data.get('id')
        print(f"=== Analyzing form content for relationships: {form_id} ===")
        
        # Get detailed form data to analyze content
        form_url = f'https://developer.api.autodesk.com/construction/forms/v1/projects/{project_id}/forms/{form_id}'
        response = requests.get(form_url, headers=headers)
        
        if not response.ok:
            print(f"Could not get detailed form data: {response.status_code}")
            return []
        
        form_details = response.json()
        
        # Extract form text content for analysis
        form_text = ""
        custom_values = form_details.get('customValues', [])
        
        for value in custom_values:
            if value.get('textVal'):
                form_text += f" {value.get('textVal')}"
            if value.get('numberVal'):
                form_text += f" {value.get('numberVal')}"
            if value.get('dateVal'):
                form_text += f" {value.get('dateVal')}"
        
        print(f"Form text for matching (first 200 chars): {form_text[:200]}...")
        
        # Look for asset references in form content (like the working code does)
        asset_references = []
        
        # Check for EOT Reference Number pattern (like in the working code)
        for value in custom_values:
            if value.get('itemLabel', '').lower().find('eot reference number') != -1:
                ref_number = value.get('textVal', '')
                if ref_number:
                    print(f"Found EOT Reference Number: {ref_number}")
                    asset_references.append({
                        'id': None,
                        'name': ref_number,
                        'description': f"EOT Reference Number: {value.get('itemLabel', '')}",
                        'type': 'field_reference',
                        'match_reason': f"Found in field: {value.get('itemLabel', '')}",
                        'clientAssetId': ref_number,
                        'locationId': 'N/A',
                        'barcode': 'N/A',
                        'relationship_id': f"EOT_REF_{form_id}"
                    })
        
        # Also check for any other asset-like patterns in the form
        # Look for patterns that might be asset IDs or references
        import re
        
        # Look for asset ID patterns (UUID-like strings)
        asset_id_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
        asset_ids = re.findall(asset_id_pattern, form_text)
        
        for asset_id in asset_ids:
            if asset_id != form_id:  # Don't include the form's own ID
                print(f"Found potential asset ID in form content: {asset_id}")
                asset_references.append({
                    'id': asset_id,
                    'name': f"Asset {asset_id[:8]}...",
                    'description': f"Found asset ID in form content: {asset_id}",
                    'type': 'content_reference',
                    'match_reason': f"Found asset ID in form text: {asset_id}",
                    'clientAssetId': 'N/A',
                    'locationId': 'N/A',
                    'barcode': 'N/A',
                    'relationship_id': f"CONTENT_REF_{form_id}_{asset_id[:8]}"
                })
        
        print(f"Found {len(asset_references)} asset references in form content")
        return asset_references
        
    except Exception as e:
        print(f"Error analyzing form content: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def find_relationships_for_form(form_id, project_id, headers):
    """Find all relationships for a specific form using project_relationships.py logic"""
    try:
        print(f"=== Finding relationships for form: {form_id} ===")
        
        # Get all relationships for the project (using the working logic from project_relationships.py)
        all_relationships = search_project_relationships(project_id, headers)
        
        form_relationships = []
        
        # Look through all relationships to find ones that include this form
        for relationship in all_relationships:
            entities = relationship.get('entities', [])
            
            # Check if this form is involved in this relationship
            form_involved = False
            other_entities = []
            
            for entity in entities:
                entity_type = entity.get('type')
                entity_id = entity.get('id')
                
                # Clean the entity ID if it has URN prefix
                clean_entity_id = entity_id
                if entity_id.startswith('urn:adsk.wipprod:dm.lineage:'):
                    clean_entity_id = entity_id.split(':')[-1]
                
                if entity_type == 'form' and clean_entity_id == form_id:
                    form_involved = True
                elif entity_type == 'asset':
                    # Get asset details
                    asset_details = get_asset_details(clean_entity_id, project_id, headers)
                    if asset_details:
                        # Get location details
                        location_id = asset_details.get('locationId', '')
                        location_details = get_location_details(location_id, project_id, headers)
                        
                        other_entities.append({
                            'id': clean_entity_id,
                            'name': asset_details.get('name', 'Unknown Asset'),
                            'description': asset_details.get('description', ''),
                            'clientAssetId': asset_details.get('clientAssetId', ''),
                            'locationId': asset_details.get('locationId', ''),
                            'locationName': location_details.get('name', 'N/A'),
                            'barcode': asset_details.get('barcode', ''),
                            'type': 'asset',
                            'relationship_id': relationship.get('id')
                        })
            
            if form_involved and other_entities:
                form_relationships.extend(other_entities)
        
        print(f"Found {len(form_relationships)} relationships for form {form_id}")
        return form_relationships
        
    except Exception as e:
        print(f"Error finding relationships for form: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def search_form_relationships(form_data, project_id, headers):
    """
    Search for relationships involving a specific form using the relationships:search endpoint
    """
    try:
        form_id = form_data.get('id')
        print(f"=== Searching relationships for form: {form_id} ===")
        
        # Get form entity info
        form_entity = get_form_entity_info(form_data, project_id, headers)
        if not form_entity:
            print("Could not determine form entity info")
            return []
        
        # Try different container ID formats
        container_ids = [project_id, f'b.{project_id}']
        
        for container_id in container_ids:
            print(f"Trying container ID: {container_id}")
            
            # Search for relationships involving this form
            search_url = f'https://developer.api.autodesk.com/bim360/relationship/v2/containers/{container_id}/relationships:search'
            
            # Search parameters for the form
            params = {
                'domain': form_entity['domain'],
                'type': form_entity['type'],
                'id': form_entity['id'],
                'pageLimit': 100
            }
            
            print(f"Searching relationships with URL: {search_url}")
            print(f"Search parameters: {params}")
            
            response = requests.get(search_url, headers=headers, params=params)
            print(f"Relationship search response status: {response.status_code}")
            
            if response.ok:
                data = response.json()
                relationships = data.get('relationships', [])
                print(f"Found {len(relationships)} relationships for form {form_id}")
                
                references = []
                for relationship in relationships:
                    relationship_id = relationship.get('id')
                    entities = relationship.get('entities', [])
                    
                    # Process each entity in the relationship
                    for entity in entities:
                        entity_domain = entity.get('domain')
                        entity_type = entity.get('type')
                        entity_id = entity.get('id')
                        
                        # If this is an asset, get its details
                        if entity_type == 'asset':
                            asset_details = get_asset_details(entity_id, project_id, headers)
                            if asset_details:
                                references.append({
                                    'id': entity_id,
                                    'name': asset_details.get('name', f"Asset ({entity_id})"),
                                    'description': asset_details.get('description', ''),
                                    'clientAssetId': asset_details.get('clientAssetId', ''),
                                    'locationId': asset_details.get('locationId', ''),
                                    'barcode': asset_details.get('barcode', ''),
                                    'type': 'asset',
                                    'relationship_id': relationship_id
                                })
                
                if references:
                    print(f"Found {len(references)} asset references for form {form_id}")
                    return references
                else:
                    print(f"No asset references found for form {form_id}")
                    return []
            else:
                print(f"Relationship search failed: {response.status_code} - {response.text}")
        
        return []
        
    except Exception as e:
        print(f"Error searching form relationships: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_form_with_relationships(form_data, project_id, headers):
    """
    Get form data with its related assets
    """
    try:
        # Get the form's relationships
        related_assets = search_form_relationships(form_data, project_id, headers)
        
        # Add the relationships to the form data
        form_data['related_assets'] = related_assets
        form_data['asset_count'] = len(related_assets)
        
        return form_data
        
    except Exception as e:
        print(f"Error getting form with relationships: {str(e)}")
        form_data['related_assets'] = []
        form_data['asset_count'] = 0
        return form_data

@app.route('/api/cache/stats')
def get_cache_stats():
    """Get cache statistics and performance metrics"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        conn = sqlite3.connect(CACHE_FILE)
        cursor = conn.cursor()
        
        # Get cache statistics
        cursor.execute('SELECT COUNT(*) FROM location_cache')
        location_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM forms_cache')
        forms_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM relationships_cache')
        relationships_count = cursor.fetchone()[0]
        
        # Get cache file size
        cache_size = get_cache_file_size()
        cache_size_mb = cache_size / 1024 / 1024
        
        # Get oldest and newest entries
        cursor.execute('SELECT MIN(last_accessed), MAX(last_accessed) FROM location_cache')
        location_dates = cursor.fetchone()
        
        cursor.execute('SELECT MIN(last_accessed), MAX(last_accessed) FROM forms_cache')
        forms_dates = cursor.fetchone()
        
        cursor.execute('SELECT MIN(last_accessed), MAX(last_accessed) FROM relationships_cache')
        relationships_dates = cursor.fetchone()
        
        # Get memory cache size
        memory_cache_size = len(location_cache)
        
        conn.close()
        
        return jsonify({
            'cache_file_size_mb': round(cache_size_mb, 2),
            'cache_size_threshold_mb': CACHE_SIZE_THRESHOLD / 1024 / 1024,
            'location_cache_entries': location_count,
            'forms_cache_entries': forms_count,
            'relationships_cache_entries': relationships_count,
            'memory_cache_entries': memory_cache_size,
            'max_projects': CACHE_MAX_PROJECTS,
            'cleanup_days': CACHE_CLEANUP_DAYS,
            'location_cache_oldest': location_dates[0] if location_dates[0] else None,
            'location_cache_newest': location_dates[1] if location_dates[1] else None,
            'forms_cache_oldest': forms_dates[0] if forms_dates[0] else None,
            'forms_cache_newest': forms_dates[1] if forms_dates[1] else None,
            'relationships_cache_oldest': relationships_dates[0] if relationships_dates[0] else None,
            'relationships_cache_newest': relationships_dates[1] if relationships_dates[1] else None,
            'cache_health': {
                'size_ok': cache_size <= CACHE_SIZE_THRESHOLD,
                'project_count_ok': location_count <= CACHE_MAX_PROJECTS,
                'needs_cleanup': cache_size > CACHE_SIZE_THRESHOLD or location_count > CACHE_MAX_PROJECTS
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting cache stats: {str(e)}'}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache_endpoint():
    """Manually clear the cache"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        clear_cache_file()
        return jsonify({'message': 'Cache cleared successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Error clearing cache: {str(e)}'}), 500

def get_all_relationships_for_project(project_id, headers):
    """Get all relationships for a project once and cache them with SQLite"""
    # Check cache size before proceeding
    check_cache_size()
    
    # Clean up old entries periodically
    cleanup_old_cache_entries()
    
    # Clean project ID
    clean_project_id = project_id.replace('b.', '') if project_id.startswith('b.') else project_id
    
    # Check SQLite cache
    try:
        conn = sqlite3.connect(CACHE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT relationships_data FROM relationships_cache 
            WHERE project_id = ?
        ''', (clean_project_id,))
        
        result = cursor.fetchone()
        if result:
            cached_relationships = json.loads(result[0])
            print(f"✅ Using cached relationships for project: {clean_project_id}")
            
            # Update last accessed timestamp
            cursor.execute('''
                UPDATE relationships_cache 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE project_id = ?
            ''', (clean_project_id,))
            conn.commit()
            conn.close()
            return cached_relationships
        else:
            print(f"📥 No cached relationships found for project: {clean_project_id}")
            conn.close()
            
    except Exception as e:
        print(f"⚠️ Error checking relationships cache: {e}")
    
    # Fetch relationships from API if not cached
    print(f"📥 Fetching relationships from API for project: {clean_project_id}")
    try:
        # Use the existing search_project_relationships function
        relationships_data = search_project_relationships(clean_project_id, headers)
        
        # Cache the relationships data in SQLite
        try:
            conn = sqlite3.connect(CACHE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO relationships_cache (project_id, relationships_data, created_at, last_accessed)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (clean_project_id, json.dumps(relationships_data)))
            
            conn.commit()
            conn.close()
            print(f"💾 Cached relationships for project: {clean_project_id}")
            
        except Exception as e:
            print(f"⚠️ Error caching relationships data: {e}")
        
        return relationships_data
        
    except Exception as e:
        print(f"❌ Error fetching relationships: {e}")
        return []

def find_relationships_for_form_cached(form_id, project_id, headers, cached_relationships):
    """Find relationships for a specific form using cached relationships data"""
    try:
        print(f"🔍 Finding relationships for form: {form_id} (using cached data)")
        
        # Filter relationships that contain this form as an entity
        form_relationships = []
        
        for relationship in cached_relationships:
            # Check if this relationship has entities
            entities = relationship.get('entities', [])
            
            # Look for a form entity with the matching form ID
            for entity in entities:
                if entity.get('type') == 'form' and entity.get('id') == form_id:
                    form_relationships.append(relationship)
                    break  # Found this form in this relationship, move to next relationship
        
        print(f"✅ Found {len(form_relationships)} relationships for form {form_id}")
        return form_relationships
        
    except Exception as e:
        print(f"❌ Error finding relationships for form {form_id}: {str(e)}")
        return []

if __name__ == '__main__':
    # Initialize cache database
    init_cache_database()
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 8080))
    print(f"Environment PORT variable: {os.environ.get('PORT')}")
    print(f"Using port: {port}")
    
    # Run the Flask app
    # Use debug mode only if explicitly set in environment
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode) 