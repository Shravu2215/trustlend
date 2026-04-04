// TrustLend — main.js


// Navbar scroll effect
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (nav) nav.style.boxShadow = window.scrollY > 20 ? '0 4px 30px rgba(0,0,0,0.4)' : 'none';
});

// Animate bar fills on scroll
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.querySelectorAll('.bar-fill, .signal-bar-fill').forEach(b => {
        b.style.width = b.getAttribute('data-w') || b.style.width;
      });
    }
  });
}, { threshold: 0.3 });
document.querySelectorAll('.signal-bars, .signals-breakdown').forEach(el => observer.observe(el));

// Set data-w from initial inline widths
document.querySelectorAll('.bar-fill, .signal-bar-fill').forEach(b => {
  b.setAttribute('data-w', b.style.width);
  b.style.width = '0%';
});

// Toast notification
function toast(msg, type = 'success') {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:24px;right:24px;background:${type==='success'?'#00ff88':'#ef4444'};color:#000;padding:14px 24px;border-radius:10px;font-family:'Syne',sans-serif;font-weight:700;font-size:15px;z-index:99999;animation:fadeUp 0.3s ease;box-shadow:0 8px 30px rgba(0,0,0,0.3);`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
window.toast = toast;

// Hamburger menu
const ham = document.getElementById('ham');
const navLinks = document.querySelector('.nav-links');
if (ham && navLinks) {
  ham.addEventListener('click', () => {
    navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
    navLinks.style.flexDirection = 'column';
    navLinks.style.position = 'absolute';
    navLinks.style.top = '70px';
    navLinks.style.left = '0';
    navLinks.style.right = '0';
    navLinks.style.background = '#080b14';
    navLinks.style.padding = '20px';
    navLinks.style.borderBottom = '1px solid #1e2d45';
    navLinks.style.zIndex = '9998';
  });
}
