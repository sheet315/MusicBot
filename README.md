
# Discord Music Bot

A simple Discord music bot built with discord.py that supports slash commands, hybrid commands, and plays music from YouTube. The bot uses a .env file to securely store the Discord bot token.

## Features
- **Slash Command Syncing**: Sync slash commands with `/sync`.
- **Music Commands**:
  - `!join`: Makes the bot join the user's voice channel.
  - `!leave`: Disconnects the bot from the voice channel.
  - `!play <url>`: Plays a YouTube video’s audio in the voice channel.
  - `!stop`: Stops the currently playing audio.
- **Environment Variable for Token**: Securely loads the bot token from a .env file.

## Prerequisites
- **Python**: Ensure you have Python 3.8 or higher installed.
- **FFmpeg**: Install FFmpeg and add it to your system's PATH. You can download it from [FFmpeg.org](https://ffmpeg.org/).

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/sheet315/MusicBot
   cd MusicBot
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or run installrequirements.bat
   
3. Edit the `.env` file in the project directory to add your Discord bot token:
   ```
   DISCORD_TOKEN=your-bot-token-here
   ```
4. Run the bot:
   ```bash
   python MAIN.py
   ```

## Usage

### Commands

| Command            | Description                                           |
|--------------------|-------------------------------------------------------|
| `/sync`            | Syncs slash commands (owner-only).                    |
| `!join`            | Makes the bot join the user's voice channel.          |
| `!leave`           | Disconnects the bot from the voice channel.           |
| `!play <url>`      | Plays a YouTube video’s audio in the voice channel.   |
| `!stop`            | Stops the currently playing audio.                    |

### Example
1. Use `!join` to make the bot join your voice channel.
2. Use `!play <YouTube URL>` to play a song.
3. Use `!stop` to stop the music.
4. Use `!leave` to disconnect the bot.

## Troubleshooting

- **Missing or Invalid Token**: If the bot token is missing or invalid, the bot will print an error message to the console and exit. Ensure your `.env` file contains the correct token.
- **FFmpeg Not Found**: Ensure FFmpeg is installed and added to your system's PATH. If it's not recognized, the bot will not be able to play audio.

## Contributing

Feel free to fork this repository and submit pull requests for new features or bug fixes. Contributions are always welcome!

## License

This project is licensed under the MIT License. See the LICENSE file for details.
```
