"""EFG Training · temporizador de descansos (interfaz adaptable a celular)."""

import streamlit as st
import streamlit.components.v1 as components


def render_rest_timer() -> None:
    """Cronómetro del navegador; no guarda datos ni requiere permisos."""
    st.markdown("### ⏱️ Temporizador de descansos")
    st.caption(
        "Elegí 3:00, 2:00 o 1:30 minutos. Funciona en la pestaña abierta; "
        "en iPhone el aviso sonoro puede no activarse si bloqueás la pantalla."
    )
    components.html(
        r"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
:root{color-scheme:dark;--bg:#171328;--line:#4b315e;--violet:#a855f7;--cyan:#22d3ee;--pink:#f472b6}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:transparent;color:#f5efff;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:750px;margin:0 auto;padding:20px 18px 22px;border:1px solid #4b315e;border-radius:24px;
background:radial-gradient(circle at 52% -24%,#3e225e 0%,transparent 65%),linear-gradient(145deg,#1b1530,#100d20)}
.presets{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-bottom:22px}
.preset{appearance:none;border:1px solid #66507c;background:#28203d;color:#dbccef;border-radius:14px;
padding:12px 20px;font-size:17px;font-weight:800;min-width:106px;cursor:pointer;touch-action:manipulation}
.preset.active{border-color:#c391ff;background:#5d2598;color:white;box-shadow:0 0 0 2px #a855f73b}
.ring{width:min(275px,70vw);height:min(275px,70vw);margin:8px auto 18px;border-radius:100%;padding:12px;
background:conic-gradient(var(--violet) 0%,#342547 0%);box-shadow:0 0 48px #7c3aed21}
.ringinner{display:flex;align-items:center;justify-content:center;flex-direction:column;width:100%;height:100%;
border-radius:100%;background:#100d20}
#clock{font-variant-numeric:tabular-nums;font-weight:900;letter-spacing:-.06em;font-size:clamp(65px,15vw,89px);line-height:1.1}
#status{color:#baa3d8;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.13em;margin-top:8px}
.actions{display:flex;gap:11px;justify-content:center;flex-wrap:wrap}
.action{appearance:none;cursor:pointer;border-radius:15px;border:1px solid #594071;padding:13px 20px;
font-weight:800;font-size:16px;min-width:132px;touch-action:manipulation;color:#f7edff;background:#332346}
.action.primary{background:linear-gradient(100deg,#7c3aed,#c026d3);border-color:#c18bfb}
.action:focus-visible,.preset:focus-visible{outline:3px solid var(--cyan);outline-offset:2px}
.note{text-align:center;color:#a99abd;font-size:12px;margin-top:16px;line-height:1.5}
@media(max-width:480px){.wrap{padding:16px 9px}.preset{min-width:90px;padding:11px 12px}.actions{gap:7px}.action{min-width:100px;padding:12px 12px}}
</style>
</head>
<body>
<div class="wrap">
 <div class="presets" aria-label="Duración del descanso">
  <button type="button" class="preset active" data-seconds="180">3:00 min</button>
  <button type="button" class="preset" data-seconds="120">2:00 min</button>
  <button type="button" class="preset" data-seconds="90">1:30 min</button>
 </div>
 <div id="ring" class="ring">
  <div class="ringinner">
   <div id="clock" role="timer" aria-label="Tiempo restante">03:00</div>
   <div id="status" aria-live="polite">Listo para empezar</div>
  </div>
 </div>
 <div class="actions">
  <button type="button" id="start" class="action primary">▶ Iniciar</button>
  <button type="button" id="pause" class="action">Ⅱ Pausar</button>
  <button type="button" id="reset" class="action">↺ Reiniciar</button>
 </div>
 <div class="note">El temporizador sigue la hora real aunque cambies de pestaña.
 Mantené la pantalla activa para oír el aviso de finalización.</div>
</div>
<script>
(function(){
  "use strict";
  var storageKey="efg-training-rest-timer-v1";
  var selected=180, remaining=180000, deadline=0, running=false, finished=false, audio=null;
  var clock=document.getElementById("clock"), ring=document.getElementById("ring");
  var status=document.getElementById("status"), start=document.getElementById("start");
  var options=Array.from(document.querySelectorAll(".preset"));
  function read(){
    try{
      var record=JSON.parse(localStorage.getItem(storageKey) || "null");
      if(record && [90,120,180].includes(record.selected)){
        selected=record.selected;
        remaining=Math.max(0,Math.min(selected*1000,Number(record.remaining)||0));
        deadline=Number(record.deadline)||0;
        running=Boolean(record.running);
        finished=Boolean(record.finished);
      }
    }catch(e){}
  }
  function save(){
    try{localStorage.setItem(storageKey,JSON.stringify({
      selected:selected,remaining:remaining,deadline:deadline,running:running,finished:finished
    }));}catch(e){}
  }
  function setupAudio(){
    try{
      if(!audio){
        var Audio=window.AudioContext||window.webkitAudioContext;
        if(Audio)audio=new Audio();
      }
      if(audio && audio.state==="suspended")audio.resume();
    }catch(e){}
  }
  function chime(){
    try{
      if(!audio)return;
      setupAudio();
      var t=audio.currentTime;
      [0,.21,.42].forEach(function(delay){
        var osc=audio.createOscillator(), gain=audio.createGain();
        osc.type="sine";osc.frequency.value=880;
        gain.gain.setValueAtTime(0.001,t+delay);
        gain.gain.exponentialRampToValueAtTime(0.2,t+delay+.02);
        gain.gain.exponentialRampToValueAtTime(.001,t+delay+.17);
        osc.connect(gain);gain.connect(audio.destination);
        osc.start(t+delay);osc.stop(t+delay+.18);
      });
    }catch(e){}
    try{if(navigator.vibrate)navigator.vibrate([180,100,180]);}catch(e){}
  }
  function display(){
    var secs=Math.ceil(remaining/1000);
    var minutes=String(Math.floor(secs/60)).padStart(2,"0");
    var seconds=String(secs%60).padStart(2,"0");
    clock.textContent=minutes+":"+seconds;
    var pct=Math.max(0,Math.min(100,100*remaining/(selected*1000)));
    ring.style.background="conic-gradient(#a855f7 0% "+pct+"%, #342547 "+pct+"% 100%)";
    status.textContent=finished?"¡Descanso terminado!":running?"Descansando":remaining<selected*1000?"En pausa":"Listo para empezar";
    start.textContent=running?"▶ En curso":remaining<selected*1000&&remaining>0?"▶ Continuar":"▶ Iniciar";
    start.disabled=running;
    start.style.opacity=running?".55":"1";
    options.forEach(function(b){
      var on=Number(b.dataset.seconds)===selected;
      b.classList.toggle("active",on);
      b.setAttribute("aria-pressed",String(on));
    });
  }
  function tick(){
    if(running){
      remaining=Math.max(0,deadline-Date.now());
      if(remaining===0){running=false;finished=true;save();chime();}
    }
    display();
  }
  read();
  if(running && deadline<=Date.now()){remaining=0;running=false;finished=true;save();}
  options.forEach(function(button){
    button.addEventListener("click",function(){
      selected=Number(button.dataset.seconds);
      remaining=selected*1000;deadline=0;running=false;finished=false;
      save();display();
    });
  });
  start.addEventListener("click",function(){
    setupAudio();
    if(remaining===0){remaining=selected*1000;}
    deadline=Date.now()+remaining;running=true;finished=false;
    save();display();
  });
  document.getElementById("pause").addEventListener("click",function(){
    if(running){remaining=Math.max(0,deadline-Date.now());running=false;finished=false;save();}
    display();
  });
  document.getElementById("reset").addEventListener("click",function(){
    running=false;finished=false;deadline=0;remaining=selected*1000;save();display();
  });
  tick();
  setInterval(tick,200);
})();
</script>
</body>
</html>""",
        height=470,
        scrolling=False,
    )
