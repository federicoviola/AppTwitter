<p align="center">
  <h1 align="center">🐦 AppTwitter</h1>
  <p align="center">
    <strong>AI-Powered Twitter/X Automation for Content Creators</strong>
  </p>
  <p align="center">
    Automate the promotion of your LinkedIn and Substack articles while generating engaging tweets that match your unique voice and style.
  </p>
</p>

<p align="center">
  <a href="https://www.gnu.org/licenses/gpl-3.0">
    <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  </a>
  <a href="https://python-poetry.org/">
    <img src="https://img.shields.io/badge/poetry-managed-blueviolet" alt="Poetry">
  </a>
  <img src="https://img.shields.io/badge/platform-Linux-lightgrey" alt="Platform: Linux">
</p>

---

## ✨ Features

### 🤖 AI-Powered Content Generation
- **Multi-Platform Support**: Twitter/X and LinkedIn
- **Multiple LLM Support**: Gemini (recommended), OpenAI, or Anthropic
- **Voice Profile**: Define your tone, themes, and argumentative patterns
- **Smart Templates**: Fallback system when LLM is unavailable
- **Content Types**: Promotional posts, thought pieces, questions, insights, and stories

### 📥 Article Import
- Import from **CSV** or **JSON** files
- Support for **LinkedIn** and **Substack** articles
- Interactive article addition mode
- Automatic metadata extraction (links, titles)

### 🛡️ Safety & Quality
- **Duplicate Detection**: Semantic similarity filtering
- **Prohibited Words**: Block unwanted content
- **Aggressive Language Filter**: Keep your brand safe
- **Human Review**: Required by default before publishing everything

### 📅 Unified Smart Scheduling
- **Cross-Platform Queue**: Manage Twitter and LinkedIn from a single view
- **Time Window**: Configure your optimal posting hours
- **Spacing Control**: Minimum time between posts
- **Daily Limits**: Respect platform guidelines (LinkedIn/X)
- **Unified Daemon Mode**: Run one process to publish on both platforms

### 🔒 Privacy-First
- **100% Local**: All data stored on your machine
- **No Cloud Dependencies**: Works offline (except for LLM/APIs)
- **SQLite Database**: Portable and lightweight
- **Secure Credentials**: Environment variables only

---

## 🚀 Quick Start

### Prerequisites

- **Linux** (Ubuntu 20.04+ recommended)
- **Python 3.11+**
- **Poetry** (dependency manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/federicoviola/AppTwitter.git
cd AppTwitter

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install Gemini support (recommended)
poetry install -E llm-gemini

# Initialize the application
./app.sh init
```

### Configuration

1. **Set up X (Twitter) credentials** in `.env`:
```bash
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

2. **Add your Gemini API key** (free tier available):
```bash
GEMINI_API_KEY=your_gemini_api_key
```
Get your key at: https://aistudio.google.com/app/apikey

3. **Set up LinkedIn credentials** in `.env`:
```bash
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```
Get your credentials at: https://www.linkedin.com/developers/apps

Then authenticate:
```bash
./app.sh linkedin-auth
```

4. **Configure your voice profile**:
```bash
./app.sh edit-voice
```

---

## 📖 Usage

### Complete Workflow

```bash
# 1. Import your articles
./app.sh import-articles --file articles.csv

# 2. Generate content for LinkedIn & Twitter
./app.sh generate --mix "promo:5,thought:3"
./app.sh linkedin-generate --mix "promo:5,story:2"

# 3. Review and approve
./app.sh review            # Review Twitter candidates
./app.sh linkedin-review   # Review LinkedIn candidates

# 4. Schedule approved content
./app.sh schedule          # Schedule Twitter
./app.sh linkedin-schedule # Schedule LinkedIn

# 5. List everything scheduled
./app.sh list-scheduled

# 6. Run the unified publisher (daemon mode)
./app.sh run --daemon --interval 300
```

### Command Reference

| Command | Description |
|---------|-------------|
| `init` | Initialize app (create config files) |
| `import-articles` | Import articles from CSV/JSON |
| `add-article` | Add article interactively |
| `list-articles` | List imported articles |
| `generate` | Generate Twitter candidates |
| `linkedin-generate` | Generate LinkedIn candidates |
| `review` | Review and approve Twitter posts |
| `linkedin-review` | Review and approve LinkedIn posts |
| `schedule` | Schedule approved Twitter tweets |
| `linkedin-schedule` | Schedule approved LinkedIn posts |
| `list-scheduled` | Show ALL scheduled posts (X + LinkedIn) |
| `run` | Unified publisher (publishes both platforms) |
| `stats` | Show statistics (global) |
| `edit-voice` | Edit voice profile |
| `linkedin-auth` | Authenticate with LinkedIn (OAuth) |
| `linkedin-status` | Check LinkedIn connection status |
| `linkedin-post` | Publish a post to LinkedIn manually |
| `linkedin-logout` | Log out from LinkedIn |
| `export` | Export tweets to file |

### Tweet Types

- **promo**: Article promotion with link
- **thought**: Brief thought or insight (no link)
- **question**: Open-ended question for engagement
- **thread**: First tweet of a thread

---

## 🏗️ Architecture

```
AppTwitter/
├── src/
│   ├── cli.py          # CLI interface (Click + Rich)
│   ├── db.py           # SQLite database management
│   ├── ingest.py       # Article import
│   ├── voice.py        # Voice profile handling
│   ├── generator.py    # Tweet generation (LLM/templates)
│   ├── filters.py      # Safety filters
│   ├── scheduler.py    # Queue and scheduling
│   ├── x_client.py     # X API client (Tweepy)
│   └── utils.py        # Utilities
├── data/
│   └── tweets.db       # SQLite database
├── logs/
│   └── app.log         # Application logs
├── .env                # Configuration (credentials)
├── voz.yaml            # Voice profile
└── app.sh              # Helper script
```

### Database Schema

| Table | Purpose |
|-------|---------|
| `articulos` | Imported articles |
| `tweet_candidates` | Generated tweets |
| `tweet_queue` | Publication queue |
| `tweets_publicados` | Published tweet history |
| `settings` | App configuration |
| `logs` | Event logs |

### Queue States

```
drafted → approved → scheduled → posted
                  ↘ skipped    ↘ failed
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

```bash
# X (Twitter) API Credentials
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

# LLM API Keys (choose one)
GEMINI_API_KEY=          # Recommended (free tier)
OPENAI_API_KEY=          # Alternative
ANTHROPIC_API_KEY=       # Alternative

# Publishing Settings
AUTO_POST_ENABLED=false  # Enable automatic posting
MAX_TWEETS_PER_DAY=3     # Daily tweet limit
MIN_SPACING_MINUTES=120  # Minimum time between tweets

# Time Window (24h format)
POST_WINDOW_START=09:00
POST_WINDOW_END=22:00
```

### Voice Profile (`voz.yaml`)

```yaml
perfil:
  nombre: "Your Name"
  bio: "Your bio for context"

temas:
  principales:
    - "AI"
    - "Philosophy"
    - "Technology"

tono:
  formal: true
  academico: false
  critico: true

ejemplos:
  - "Example tweet 1"
  - "Example tweet 2"
  - "Example tweet 3"

generacion:
  temperatura: 0.7
  max_tokens: 280
```

---

## 🛡️ Terms of Use

This application:
- Uses **only the official X API**
- **Respects X Terms of Service**
- Implements **conservative rate limits**
- Requires **human review by default**
- Does **not** attempt to bypass any restrictions

---

## 🐛 Troubleshooting

### "X API not available"
- Check credentials in `.env`
- Verify API access at [developer.twitter.com](https://developer.twitter.com)
- Use export mode: `./app.sh export`

### "LLM not available"
- Works without LLM (uses templates)
- To enable: `poetry install -E llm-gemini`
- Add `GEMINI_API_KEY` to `.env`

### "No approved tweets"
- Run `./app.sh review` first

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

This means:
- ✅ You can use, modify, and distribute this software
- ✅ You can use it for commercial purposes
- ⚠️ Any derivative work must also be GPL v3 licensed
- ⚠️ You must disclose the source code of derivative works

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🙏 Credits

Built with:
- [Python 3.11+](https://www.python.org/)
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Tweepy](https://www.tweepy.org/) - X API wrapper
- [Gemini](https://ai.google.dev/) - AI generation
- [SQLite](https://www.sqlite.org/) - Database

---

## 📬 Contact

**Federico Viola** - [@federicoviola](https://twitter.com/federicoviola)

Project Link: [https://github.com/federicoviola/AppTwitter](https://github.com/federicoviola/AppTwitter)

---

<p align="center">
  <strong>⚡ Made with ❤️ for content creators who value their time</strong>
</p>
