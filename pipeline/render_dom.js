/* Writes the page as its script builds it, at a given screen width, for
   check_css.py. usage: node render_dom.js index.html 390 out.html */
const {JSDOM} = require("jsdom"); const fs = require("fs");
const w0 = +process.argv[3];
const dom = new JSDOM(fs.readFileSync(process.argv[2],"utf8"), {runScripts:"dangerously", pretendToBeVisual:true, url:"https://example.test/",
  beforeParse(w){ Object.defineProperty(w,"innerWidth",{value:w0,writable:true}); w.fetch=()=>Promise.reject(new Error("x"));
    w.matchMedia=()=>({matches:false,addEventListener(){},addListener(){}}); w.scrollTo=()=>{}; w.HTMLElement.prototype.scrollIntoView=function(){}; w.CSS={escape:s=>s}; }});
setTimeout(()=>{ const d=dom.window.document; fs.writeFileSync(process.argv[4], "<!doctype html><html><head><style>"
  + d.querySelector("style").textContent + "</style></head><body>" + d.body.innerHTML + "</body></html>"); process.exit(0); }, 1300);
