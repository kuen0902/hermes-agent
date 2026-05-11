# macOS Markdown Quick Look - Installation & Troubleshooting

This guide documents how to enable rich, formatted previews for `.md` files in Finder using the Spacebar (Quick Look).

## 1. Installation
The preferred tool is `sbarex-qlmarkdown`.

```bash
brew install --cask qlmarkdown
```

## 2. Enabling the Extension
On recent macOS versions (Sequoia/Tahoe), the extension manager has moved.

**Path**: System Settings -> General -> Login Items & Extensions
1. Scroll to the bottom to find **Extensions** (圖示為紫色圓圈內有三個小方塊).
2. Click the "i" or the row to expand.
3. Select **Quick Look** (快速查看).
4. Toggle **QLMarkdown** to ON.

## 3. Activation & Cache Refresh
If the preview doesn't appear immediately, force a system refresh:

```bash
# Remove quarantine flag and launch once to register
xattr -cr /Applications/QLMarkdown.app
open /Applications/QLMarkdown.app

# Rebuild Quick Look cache
qlmanage -r && qlmanage -r cache && killall Finder
```

## 4. Troubleshooting
- **Still seeing source code?** macOS often prioritizes the internal text preview. Ensure no other Markdown editors (like MacDown or Typora) are fighting for the Quick Look priority.
- **Search fails**: Browsing the "General" menu manually is more reliable than searching "Quick Look" in Privacy settings, as the latter sometimes filters out English terms in CJK locales.
