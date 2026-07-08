# Bookmarklet Capture Setup

## Overview

A browser bookmarklet that sends the current page title and URL to the LifeOS Capture API.

## Prerequisites

- Capture API running and accessible (localhost or Tailscale)
- Bearer token configured

## Bookmarklet Code

Create a new bookmark in your browser with this URL:

```javascript
javascript:(function(){
  var t=document.title,u=window.location.href,
  d=JSON.stringify({url:u,title:t,source:"bookmarklet",client:"browser_bookmarklet"}),
  f=new XMLHttpRequest();
  f.open("POST","http://127.0.0.1:8789/captures");
  f.setRequestHeader("Content-Type","application/json");
  f.setRequestHeader("Authorization","Bearer YOUR_TOKEN_HERE");
  f.onload=function(){if(f.status===200){alert("Captured: "+t)}else{alert("Capture failed")}};
  f.send(d);
})();
```

Replace `YOUR_TOKEN_HERE` with your actual bearer token.

## How to Install

1. Copy the code above.
2. Replace `YOUR_TOKEN_HERE` with your token.
3. Create a new bookmark in your browser.
4. Set the URL to the complete JavaScript code (including `javascript:` prefix).
5. Name it "LifeOS Capture".

## Usage

- Click the bookmarklet on any page you want to capture.
- The page title and URL will be sent to the Capture API.
- A JavaScript alert will confirm capture or show failure.

## Security Warning

- **The bearer token is stored in plaintext in the bookmarklet.** Anyone with access to your browser bookmarks can see the token.
- Only use this on a machine you control.
- Use a dedicated low-privilege token for bookmarklets.
- The bookmarklet can only send requests when the Capture API is reachable (localhost or Tailscale).
