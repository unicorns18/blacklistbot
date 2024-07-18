from flask import Flask, request, render_template
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.configstuff import ConfigHandler, load_servers

app = Flask(__name__, template_folder='templates')

@app.route('/')
def home():
    servers = load_servers()
    return render_template('config.html', servers=servers, current_server_id=None)

@app.route('/config/<server_id>')
def config(server_id):
    servers = load_servers()
    server = next((s for s in servers if s['id'] == server_id), None)
    if server is None:
        return "Server not found", 404
    config_handler = ConfigHandler(server_id)
    config = config_handler.get_config()
    return render_template('config_form.html', servers=servers, current_server_id=server_id, server=server, config=config)

@app.route('/update/<server_id>', methods=['POST'])
def update_config(server_id):
    data = request.form
    config = {
        'roleid': int(data['roleid']),
        'logToChannel': 'logToChannel' in data,
        'logChannel': int(data['logChannel'])
    }
    config_handler = ConfigHandler(server_id)
    config_handler.update_config(config)
    return render_template('success.html')


if __name__ == '__main__':
    app.run(debug=True)