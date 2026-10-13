"""EFG Training · temporizador de descansos (interfaz adaptable a celular)."""

import streamlit as st
import streamlit.components.v1 as components


def render_rest_timer() -> None:
    """Cronómetro del navegador; no guarda datos ni requiere permisos."""
    st.markdown("### ⏱️ Temporizador de descansos")
    st.caption(
        "Elegí 3:00, 2:00 o 1:30 minutos. Funciona en la pestaña abierta; "
        "tocá «🔊 Probar sonido» la primera vez en iPhone para activarlo. "
        "Puede no sonar con el teléfono en silencio, bloqueado o en segundo plano."
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
.action.audio{border-color:#187c80;background:#173c48;color:#abf7ee}
.audio-status{text-align:center;font-size:12px;font-weight:700;line-height:1.5;color:#b3e4de;
margin:14px auto 0;max-width:620px}
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
  <button type="button" id="test-sound" class="action audio">🔊 Probar sonido</button>
 </div>
 <div id="audio-status" class="audio-status" role="status" aria-live="polite">
  Para activar el sonido en iPhone, tocá «Probar sonido» una vez.
 </div>
 <div class="note">Usá volumen audible y desactivá el modo silencio si no se escucha.
 El aviso funciona con el navegador abierto; iPhone puede bloquearlo con la pantalla apagada
 o cuando la app queda en segundo plano.</div>
</div>
<script>
(function(){
  "use strict";
  var storageKey="efg-training-rest-timer-v1";
  var selected=180, remaining=180000, deadline=0, running=false, finished=false;
  var audio=null, alertSound=null, soundReady=false, soundUrl=null, wakeLock=null;
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
  function soundMessage(message){
    document.getElementById("audio-status").textContent=message;
  }
  function makeSound(){
    // Alarma WAV local (sin descarga, internet ni archivos externos).
    // HTMLAudio suele funcionar mejor que WebAudio en Safari con modo silencio,
    // siempre que se habilite al pulsar un botón.
    if(alertSound)return alertSound;
    try{
      var rate=22050, samples=Math.ceil(rate*1.55);
      var buffer=new ArrayBuffer(44+samples*2), view=new DataView(buffer);
      function word(at,str){for(var j=0;j<str.length;j++)view.setUint8(at+j,str.charCodeAt(j));}
      word(0,"RIFF");view.setUint32(4,36+samples*2,true);word(8,"WAVE");
      word(12,"fmt ");view.setUint32(16,16,true);
      view.setUint16(20,1,true);view.setUint16(22,1,true);
      view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);
      view.setUint16(32,2,true);view.setUint16(34,16,true);
      word(36,"data");view.setUint32(40,samples*2,true);
      var tones=[[.08,.34,784],[.47,.75,988],[.88,1.28,1175]];
      for(var i=0;i<samples;i++){
        var sec=i/rate, val=0;
        for(var k=0;k<tones.length;k++){
          var tone=tones[k],a=tone[0],b=tone[1],hz=tone[2];
          if(sec>=a&&sec<=b){
            var envelope=Math.max(0,Math.min(1,(sec-a)/.018,(b-sec)/.065));
            val=.36*envelope*Math.sin(2*Math.PI*hz*(sec-a));
            break;
          }
        }
        view.setInt16(44+2*i,Math.round(Math.max(-1,Math.min(1,val))*32767),true);
      }
      soundUrl=URL.createObjectURL(new Blob([buffer],{type:"audio/wav"}));
      alertSound=new Audio(soundUrl);
      alertSound.preload="auto";
      alertSound.playsInline=true;
      return alertSound;
    }catch(e){return null;}
  }
  function setupAudio(){
    try{
      if(!audio){
        var Ctx=window.AudioContext||window.webkitAudioContext;
        if(Ctx)audio=new Ctx();
      }
      if(audio&&audio.state==="suspended"){
        var resumed=audio.resume();
        if(resumed&&resumed.catch)resumed.catch(function(){});
      }
    }catch(e){}
  }
  function synthFallback(){
    try{
      if(!audio||audio.state!=="running")return false;
      var t=audio.currentTime+.02;
      [[0,784],[.36,988],[.72,1175]].forEach(function(note){
        var osc=audio.createOscillator(),gain=audio.createGain();
        osc.type="sine";osc.frequency.value=note[1];
        gain.gain.setValueAtTime(.001,t+note[0]);
        gain.gain.exponentialRampToValueAtTime(.25,t+note[0]+.025);
        gain.gain.exponentialRampToValueAtTime(.001,t+note[0]+.26);
        osc.connect(gain);gain.connect(audio.destination);
        osc.start(t+note[0]);osc.stop(t+note[0]+.27);
      });
      return true;
    }catch(e){return false;}
  }
  function armSound(){
    setupAudio();
    var sound=makeSound();
    if(!sound||soundReady)return;
    try{
      // Primera reproducción iniciada directamente por el botón «Iniciar».
      // El clip comienza con 80 ms de silencio; lo pausamos antes del pitido.
      // El mismo elemento queda habilitado para reproducirse al llegar a cero.
      var attempt=sound.play();
      if(attempt&&typeof attempt.then==="function"){
        attempt.then(function(){
          sound.pause();sound.currentTime=0;soundReady=true;
          soundMessage("🔊 Aviso preparado. Podés comprobarlo con «Probar sonido».");
        }).catch(function(){
          soundMessage("Tocá «🔊 Probar sonido» para habilitar el audio del iPhone.");
        });
      }
    }catch(e){
      soundMessage("Tocá «🔊 Probar sonido» para habilitar el audio del iPhone.");
    }
  }
  function chime(fromTest){
    if(!fromTest && !finished)return;
    var sound=makeSound();
    function fallback(){
      var ok=synthFallback();
      soundMessage(ok?"Aviso emitido. Si no sonó, revisá silencio y volumen.":"El navegador bloqueó el audio. Tocá «Probar sonido» con la pantalla activa.");
    }
    if(sound){
      try{
        sound.pause();sound.currentTime=0;
        var playPromise=sound.play();
        if(playPromise&&typeof playPromise.then==="function"){
          playPromise.then(function(){
            soundReady=true;
            soundMessage(fromTest?"🔊 Prueba reproducida. Sonido preparado.":"🔔 ¡Descanso terminado! Sonó el aviso.");
          }).catch(fallback);
        }else{
          soundReady=true;
          soundMessage(fromTest?"🔊 Prueba de sonido iniciada.":"🔔 ¡Descanso terminado!");
        }
      }catch(e){fallback();}
    }else fallback();
    try{if(navigator.vibrate)navigator.vibrate([180,100,180]);}catch(e){}
  }
  function keepAwake(){
    try{
      if(navigator.wakeLock&&!wakeLock&&document.visibilityState==="visible"){
        navigator.wakeLock.request("screen").then(function(lock){
          wakeLock=lock;
          lock.addEventListener("release",function(){wakeLock=null;});
        }).catch(function(){});
      }
    }catch(e){}
  }
  function allowSleep(){
    if(wakeLock){
      try{wakeLock.release().catch(function(){});}catch(e){}
      wakeLock=null;
    }
  }
  function stopChime(){
    try{if(alertSound){alertSound.pause();alertSound.currentTime=0;}}catch(e){}
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
      if(remaining===0){running=false;finished=true;save();allowSleep();chime(false);}
    }
    display();
  }
  read();
  if(running && deadline<=Date.now()){remaining=0;running=false;finished=true;save();}
  options.forEach(function(button){
    button.addEventListener("click",function(){
      selected=Number(button.dataset.seconds);
      remaining=selected*1000;deadline=0;running=false;finished=false;
      stopChime();allowSleep();save();display();
    });
  });
  start.addEventListener("click",function(){
    stopChime();
    armSound();
    if(remaining===0){remaining=selected*1000;}
    deadline=Date.now()+remaining;running=true;finished=false;
    keepAwake();
    save();display();
  });
  document.getElementById("pause").addEventListener("click",function(){
    if(running){remaining=Math.max(0,deadline-Date.now());running=false;finished=false;allowSleep();save();}
    display();
  });
  document.getElementById("reset").addEventListener("click",function(){
    running=false;finished=false;deadline=0;remaining=selected*1000;
    stopChime();allowSleep();save();display();
  });
  document.getElementById("test-sound").addEventListener("click",function(){
    setupAudio();
    soundMessage("Reproduciendo prueba de sonido…");
    chime(true);
  });
  document.addEventListener("visibilitychange",function(){
    tick();
    if(running&&document.visibilityState==="visible")keepAwake();
  });
  tick();
  if(running)keepAwake();
  setInterval(tick,200);
})();
</script>
</body>
</html>""",
        height=550,
        scrolling=False,
    )
