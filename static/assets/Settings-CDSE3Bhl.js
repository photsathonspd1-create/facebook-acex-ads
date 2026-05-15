
import { t as getJSX } from "./react-vendor-C0IOBbdh.js";

const L = getJSX();

export default function Settings() {
  const saveToken = () => {
    const token = document.getElementById('fb-token-input').value;
    if (!token) return;
    
    fetch("/api/fb/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token })
    }).then(res => {
      if (res.ok) {
        alert("✅ Saved successfully!");
        window.location.reload();
      } else {
        alert("❌ Failed to save token");
      }
    });
  };

  const loginWithFB = () => {
    fetch("/api/auth/facebook")
      .then(res => res.json())
      .then(data => {
        if (data.redirect_url) {
          window.location.href = data.redirect_url;
        } else {
          alert("❌ Error: " + (data.error || "Failed to get redirect URL"));
        }
      });
  };

  return L.jsxs("div", {
    style: {color: '#fff', padding: '24px', background: '#1a1a1a', borderRadius: '12px', border: '1px solid #333', maxWidth: '600px', margin: '40px auto'},
    children: [
      L.jsx("h2", {style: {fontSize: '24px', fontWeight: 'bold', marginBottom: '24px'}, children: "Facebook API Setup"}),
      L.jsxs("div", {
        style: {display: 'flex', flexDirection: 'column', gap: '24px'},
        children: [
          L.jsxs("div", {
            children: [
              L.jsx("label", {style: {display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px'}, children: "Facebook Access Token"}),
              L.jsx("input", {
                id: "fb-token-input",
                type: "password",
                style: {width: '100%', background: '#0a0a0a', border: '1px solid #333', borderRadius: '8px', padding: '8px 16px', color: '#fff', outline: 'none'},
                placeholder: "EAA..."
              }),
              L.jsx("p", {style: {fontSize: '12px', color: '#888', marginTop: '8px'}, children: "ใส่ Long-lived Access Token ของคุณที่นี่"})
            ]
          }),
          L.jsx("button", {
            onClick: saveToken,
            style: {background: '#0066ff', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer'},
            children: "Save Token & Connect"
          }),
          L.jsxs("div", {
            style: {marginTop: '20px', borderTop: '1px solid #333', paddingTop: '20px'},
            children: [
              L.jsx("h3", {style: {fontSize: '16px', fontWeight: 'bold', marginBottom: '12px', color: '#ffcc00'}, children: "หรือเชื่อมต่อผ่าน Facebook OAuth"}),
              L.jsx("button", {
                onClick: loginWithFB,
                style: {background: 'transparent', color: '#0066ff', border: '1px solid #0066ff', padding: '10px 24px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer'},
                children: "Login with Facebook"
              })
            ]
          })
        ]
      })
    ]
  });
}
