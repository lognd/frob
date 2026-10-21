//! The contact sheet: one self-contained HTML page with keyboard verdicts.

// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ

use std::fmt::Write as _;

use super::store::status_name;
use crate::manifest::Status;

/// One tile of the contact sheet.
#[derive(Debug, Clone)]
pub struct Tile {
    /// Screen id.
    pub screen: String,
    /// State id.
    pub state: String,
    /// Platform id.
    pub platform: String,
    /// Current verdict, `None` when the cell has not been judged or has no render.
    pub status: Option<Status>,
    /// Whether an image exists to show.
    pub rendered: bool,
}

/// Escape `text` for an HTML text or attribute position.
pub fn escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#39;"),
            other => out.push(other),
        }
    }
    out
}

/// The contact sheet for `tiles`; `token` authorises the page's verdict requests.
pub fn render(tiles: &[Tile], token: &str) -> String {
    let mut body = String::new();
    for (i, t) in tiles.iter().enumerate() {
        let status = t.status.map_or("pending", status_name);
        let img = if t.rendered {
            format!("<img src=\"/img/{i}?t={}\" alt=\"\">", escape(token))
        } else {
            "<div class=\"none\">not rendered</div>".to_owned()
        };
        let _ = writeln!(
            body,
            "<figure id=\"c{i}\" class=\"{status}\" data-i=\"{i}\" tabindex=\"0\">{img}<figcaption>{} / {} / {} <b>{status}</b></figcaption></figure>",
            escape(&t.screen),
            escape(&t.state),
            escape(&t.platform),
        );
    }
    format!(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>crunk gallery triage</title>\
<style>body{{font:14px sans-serif;margin:1em}}main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1em}}\
figure{{margin:0;border:3px solid #999;padding:4px}}figure img{{width:100%}}figure.approved{{border-color:#2a2}}figure.rejected{{border-color:#c22}}\
figure:focus{{outline:3px solid #36f}}.none{{padding:2em;color:#777}}</style></head><body>\
<h1>crunk gallery triage</h1><p>Arrows move, <b>a</b> approve, <b>r</b> reject, <b>p</b> pending.</p>\
<button id=\"done\">Finish</button><main>\n{body}</main>\
<script>const T={token:?};\
const f=()=>[...document.querySelectorAll('figure')];\
async function v(el,s){{const r=await fetch('/verdict',{{method:'POST',headers:{{'X-Triage-Token':T}},body:JSON.stringify({{index:+el.dataset.i,status:s}})}});\
if(r.ok){{el.className=s;el.querySelector('b').textContent=s}}}}\
document.addEventListener('keydown',e=>{{const l=f();let i=l.indexOf(document.activeElement);\
if(e.key==='ArrowRight')i=Math.min(l.length-1,i+1);else if(e.key==='ArrowLeft')i=Math.max(0,i-1);\
else if(i>=0&&e.key==='a')v(l[i],'approved');else if(i>=0&&e.key==='r')v(l[i],'rejected');else if(i>=0&&e.key==='p')v(l[i],'pending');else return;\
if(l[i])l[i].focus()}});\
document.getElementById('done').onclick=async()=>{{await fetch('/done',{{method:'POST',headers:{{'X-Triage-Token':T}}}});document.body.append(' Saved. You can close this tab.')}};\
if(f()[0])f()[0].focus();</script></body></html>\n",
    )
}
