# BlacklistBot

A Discord bot that helps manage blacklists using Google Drive integration and database functionality.

## Features

- Discord server integration
- Google Drive file management
- Database support for persistent storage
- Guild (server) configuration management
- Extensible architecture with support for custom extensions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/blacklistbot.git
cd blacklistbot
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your credentials:
   - Place your Discord bot token in the appropriate location in the `credentials` directory
   - Set up Google Drive API credentials and save the `token.pickle` file

## Configuration

The bot uses `guilds.json` for server-specific configurations. Each guild can have its own settings and preferences.

## Project Structure

- `app.py` - Main bot application entry point
- `database.py` - Database interaction layer
- `drive.py` - Google Drive integration
- `extensions/` - Bot command extensions
- `utils/` - Helper utilities
- `credentials/` - Directory for storing sensitive credentials
- `guilds.json` - Server configuration file

## Usage

To start the bot:

```bash
python app.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

Copyright (c) 2024 BlacklistBot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.