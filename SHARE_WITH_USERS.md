# Hidear - Share This with Your Users

This guide helps you share Hidear with other developers and users.

---

## What to Share

### For Everyone
1. **[README.md](./README.md)** - Project overview and quick start
2. **[DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)** - Navigation guide for documentation

### For Users (Web UI)
3. **[QUICK_START.md](./QUICK_START.md)** - How to use the web interface

### For Developers (API Integration)
4. **[API_GUIDE.md](./API_GUIDE.md)** - Complete REST API reference
5. **[COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md)** - Integration examples & patterns

### For DevOps/Admins (Deployment)
6. **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Production deployment guide

---

## How to Share

### Option 1: Share the Repository
```bash
# Clone/download the entire hidear directory
git clone <your-repo-url>
cd hidear

# All documentation is included in the root directory
ls *.md
```

### Option 2: Share Individual Guides

**For non-technical users:**
```bash
# Send these files:
- README.md
- QUICK_START.md
```

**For API developers:**
```bash
# Send these files:
- API_GUIDE.md
- COMPONENT_INTEGRATION.md
```

**For DevOps teams:**
```bash
# Send these files:
- DEPLOYMENT_CHECKLIST.md
- start-services.sh
- .env (with HF_TOKEN placeholder)
```

### Option 3: Share as a Website

Host documentation on your internal wiki or website:
```bash
# Convert markdown to HTML (example with pandoc)
pandoc API_GUIDE.md -o api_guide.html
```

Or use a tool like:
- **ReadTheDocs**: Free documentation hosting
- **Gitbook**: Markdown to interactive docs
- **GitHub Pages**: Built-in for GitHub repos

---

## User Communication Template

Use this email/message template when sharing Hidear:

---

### Subject: Hidear Audio Analysis Platform - Now Available

Hi Team,

We're excited to share **Hidear**, our new AI-powered audio analysis platform!

#### What is Hidear?

Hidear can:
- 🎤 Transcribe audio (speech-to-text)
- 😊 Analyze emotions in conversations
- 👥 Identify and track speakers across meetings
- 🔄 Detect voice activity automatically

#### Get Started

**Just want to use it?**
→ Start with [QUICK_START.md](./QUICK_START.md) (10 minutes)

**Building an integration?**
→ Read [API_GUIDE.md](./API_GUIDE.md) for complete API reference

**Deploying to production?**
→ Follow [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

#### Server Access

```
Web Interface: http://your-server:5847
API Endpoint: http://your-server:9427/api/v1
API Docs: http://your-server:9427/api/docs
```

#### Key Features in This Release

- ✨ Speaker enrollment with just 1 audio file (previously 2-5)
- ✨ Smart speaker detection (up to 100+ speakers)
- ✨ Review queue for unidentified speakers
- ✨ Real-time voice activity detection
- ✨ Full transcription + emotion analysis

#### Need Help?

1. Check the [Documentation Index](./DOCUMENTATION_INDEX.md)
2. Review interactive API docs: `http://your-server:9427/api/docs`
3. Check logs: `podman logs hidear-backend`

---

## File Distribution Guide

### Distribution 1: Complete Package (All Users)
```
hidear/
├── README.md                      ← Start here!
├── DOCUMENTATION_INDEX.md         ← Navigation guide
├── QUICK_START.md                ← For users
├── API_GUIDE.md                  ← For developers
├── COMPONENT_INTEGRATION.md       ← Advanced integration
├── DEPLOYMENT_CHECKLIST.md        ← For DevOps
└── start-services.sh              ← Deployment script
```

### Distribution 2: Users Only
```
Hidear User Guide/
├── README.md
├── QUICK_START.md
└── DOCUMENTATION_INDEX.md
```

### Distribution 3: Developers Only
```
Hidear API Documentation/
├── API_GUIDE.md
├── COMPONENT_INTEGRATION.md
├── README.md
└── DOCUMENTATION_INDEX.md
```

### Distribution 4: DevOps/Admins Only
```
Hidear Deployment Guide/
├── DEPLOYMENT_CHECKLIST.md
├── start-services.sh
├── stop-services.sh
├── .env
└── README.md (Infrastructure section)
```

---

## Quick Reference for Sharers

### Endpoint Status
All services are running and accessible from your server:

| Service | URL | Status |
|---------|-----|--------|
| Frontend | `http://your-server:5847` | ✅ |
| API | `http://your-server:9427` | ✅ |
| API Docs | `http://your-server:9427/api/docs` | ✅ |
| MERaLiON (internal) | `http://your-server:9428` | ✅ |

### Common Use Cases to Mention

1. **Transcribe a meeting**
   - Upload audio file
   - Get full transcript with speaker names
   - Results in 2-5 minutes

2. **Identify who spoke when**
   - Upload meeting recording
   - System automatically identifies speakers
   - See speaker names with timestamps

3. **Track emotions**
   - Full emotional analysis per speaker
   - See sentiment trends throughout meeting

4. **Build a custom integration**
   - Use REST API for any application
   - JavaScript, Python, or any language
   - Full documentation provided

---

## FAQ for Users

### Q: How much does it cost?
A: Hidear is [open-source/internal/paid - fill in as appropriate]. The core service is free to use on your organization's server.

### Q: What audio formats are supported?
A: `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.webm`
Maximum file size: 50MB

### Q: How long does processing take?
A: Typically 20-60 seconds per 5 minutes of audio, depending on server load.

### Q: Can I use it offline?
A: Hidear runs on a server. As long as you have network access to that server, you can use it. Internet is only needed at startup for model downloads.

### Q: How many speakers can it identify?
A: Up to 100+ speakers detected and tracked. Requires enrollment for accurate identification.

### Q: Is my audio data private?
A: Audio files are processed on your organization's server. See your IT team for data security policies.

---

## IT/Admin Checklist Before Sharing

Before allowing users to access Hidear:

- [ ] Confirm server is running (`podman ps`)
- [ ] Confirm API is responding (`curl http://localhost:9427/api/docs`)
- [ ] Confirm frontend is accessible (`http://localhost:5847`)
- [ ] Have you collected user requirements?
- [ ] Have you confirmed network access for all users?
- [ ] Have you configured any security/authentication?
- [ ] Have you set up monitoring/logging?
- [ ] Have you created a support process?
- [ ] Have you informed your IT security team?

---

## Support Escalation Path

For users having issues:

1. **First:** Check [QUICK_START.md](./QUICK_START.md) troubleshooting section
2. **Second:** Review [API_GUIDE.md](./API_GUIDE.md) error handling section
3. **Third:** Check server logs:
   ```bash
   podman logs hidear-backend
   podman logs hidear-celery
   ```
4. **Last:** Contact the Hidear maintainer: [your contact info]

---

## Version & Updates

**Current Version**: 2.0.0
**Last Updated**: October 27, 2024

**Breaking Changes from v1.0.0:**
- Speaker enrollment now requires minimum 1 file (was 2)
- New speaker diarization with configurable max_speakers
- Review queue system for managing unidentified speakers
- Enhanced emotion analysis

**To Update:**
```bash
git pull origin main
./start-services.sh
```

---

## Feedback & Suggestions

Users can provide feedback through:
- [GitHub Issues](link-to-your-repo)
- [Email](your-email@company.com)
- [Internal Chat](link-to-slack-channel)

---

## Thank You!

Thanks for using Hidear. We hope it helps your organization better understand audio conversations!

**Questions?** Start with the [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)

---

**Hidear v2.0.0**
**Made with ❤️ for intelligent audio processing**
