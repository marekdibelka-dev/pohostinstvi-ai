# Pohostinství AI Cloud v1.4 – Facebook

Existing Slack bot continues to accept Czech beer changes from **all members** of the private `#piva-na-cepu` channel.

## Automatic Facebook posts

- On **Friday and Saturday 18:00–21:00**, **Sunday 16:00–20:00**, `Europe/Prague` time.
- **Only if a new Slack message reports a complete beer replacement with explicit price**. The old beer is not modified in Dotykačka (API not connected).
- Posts **one photo with caption**, without human approval, to a **Facebook Page**. No Instagram, no website changes.
- Outside those hours: **no posting and no queue** (prevents advertising a beer that may have run out before the next opening window).
- Same Slack event never deliberately posted twice: persistent SQLite ID-based deduplication; uncertain Facebook outcomes require manual check.
- Current original infographic is a **placeholder template**, not an exact match to past graphics. Supply a sample infographic to adapt it.

## Before turning on auto-posting

1. Create/configure a Meta developer app with access to the target Page, a Page access token, and permissions `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`. Some accounts require Meta App Review / Advanced Access. The person/token must have content creation access to the Page.
2. On Railway service **web**, add a **persistent volume** mounted at `/data` and set `FB_DB_PATH=/data/pohostinstvi_ai.sqlite3`.
3. Set `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN` in **Railway Variables**, not in source code or Slack.
4. Test with `FB_AUTO_PUBLISH=0` first. The Slack bot responds with a Facebook text preview during eligible windows.
5. After validating access, Page destination and visual design, set `FB_AUTO_PUBLISH=1` to enable real unattended posting.
6. Keep `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` unchanged. The bot needs Slack Event Subscriptions `message.groups` and scope `groups:history` for the private channel.

## Safeguards / limitations

- Any human member of the configured Slack channel can trigger publication; **keep it private**.
- If Facebook request times out, the system **does not retry automatically**: a post may already exist.
- Messages without a price are never posted. The parser recognizes several common Czech phrasings, not arbitrary language.
- There is no Dotykačka cross-check. If a member sends incorrect information, it can be published.
- Avoid deleting or replacing the persistent volume: that would lose deduplication history.
- The app replies in Slack threads. The endpoint is `/slack/events`, health check `/health`.

## Tests

Run `python -m unittest discover -v`.
