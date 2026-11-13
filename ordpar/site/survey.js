/*! Ordpar — the readers' survey, "Ordpar — your first impressions" (site decisions 173, Robin
 * 2026-11-07: our own page in place of the Google form, kept after launch).
 *
 *   window.ordparSurvey = {
 *     collect(form),      // {answers, follow, trap}: what the form holds, as it would be sent
 *     message(answers, follow, trap),   // what is sent, as an object
 *     wire(form),         // Send, the skipped question, the status; done once on load
 *     SURVEY_RECEIVER, MAX_ANSWER, MAX_CHOICE, MAX_FOLLOW
 *   }
 *
 * The page `/survey/` is built by the site (`ordpar/sitegen/survey.py`) from ONE data file,
 * `ordpar/site/survey.json`: its words, its questions and the ideas listed, every question optional.
 * Without script the questions show, and a line says that sending needs JavaScript. This script
 * only SENDS, and hides a question while the answer that skips it is chosen (the data file's
 * `skip_if`: "What is your first language?" while "Norwegian is my first language" is chosen; it is
 * then never sent, whatever was typed into it).
 *
 * THE SWITCH: `SURVEY_RECEIVER` below, the receiver's `/survey` address — never set here: the build
 * writes it (`sitegen/page.py` `survey_js`, from `chrome.survey_receiver()`: the reports' receiver
 * with `/survey` for `/report`, while `chrome.SURVEY` is on), and builds the page only then.
 *
 * WHAT IS SENT, and only when the reader presses Send: one JSON message — `answers`, each question
 * answered under its key (a text as written, or the choices ticked as they read; a question left
 * empty is left out), and `follow`, the follow-up address or name, or null — and, only when a robot
 * has filled it, the hidden trap field (`hp`), which makes the receiver drop the message. No cookies
 * (`credentials: 'omit'`), no referrer (`referrerPolicy: 'no-referrer'`), no page address, no
 * setting, no build, no identifier; nothing is written to storage. Offline, the page says it needs a
 * connection and keeps the answers; a failed send keeps them too. The receiver's cap is the reports'
 * (30 an hour from everyone together, reports and answers counted together): past it, the page says
 * so and keeps the answers.
 *
 * The limits are the receiver's (`ordpar/receiver/src/survey.js`; its test holds them equal): each
 * question's own `maxlength` comes from the data file, within MAX_ANSWER; a choice within
 * MAX_CHOICE; the follow-up within MAX_FOLLOW.
 */
(function (global) {
  'use strict';

  /* THE SURVEY RECEIVER'S ADDRESS. Never edited here: the build writes it into this line. */
  var SURVEY_RECEIVER = '';

  var MAX_ANSWER = 2000;    // characters of a written answer: the receiver's MAX_ANSWER
  var MAX_CHOICE = 300;     // characters of a choice: the receiver's MAX_CHOICE
  var MAX_FOLLOW = 254;     // characters of the follow-up address or name: the receiver's MAX_FOLLOW

  var doc = global.document;
  var nav = global.navigator || {};
  var words = null;

  function t(key) {
    if (!words) {
      words = {};
      var island = doc && doc.getElementById('ordpar-survey-words');
      try { words = island ? JSON.parse(island.textContent) : {}; } catch (e) { words = {}; }
    }
    return words[key] || key;
  }

  function cut(s, max) {
    s = String(s || '').trim();
    return s.length > max ? s.slice(0, max) : s;
  }

  /** The message, exactly: nothing else is ever sent. */
  function message(answers, follow, trap) {
    var m = { answers: answers || {}, follow: follow || null };
    if (trap) { m.hp = trap; }
    return m;
  }

  /** Is the question block `q` shown (not skipped by the answer chosen elsewhere)? */
  function shown(q) {
    return !q.hidden;
  }

  /** What `form` holds, as it would be sent: {answers, follow, trap}. */
  function collect(form) {
    var answers = {}, follow = '', trap = '';
    var qs = form.querySelectorAll('[data-q]');
    for (var i = 0; i < qs.length; i++) {
      var q = qs[i], key = q.getAttribute('data-q'), kind = q.getAttribute('data-kind');
      if (!shown(q)) { continue; }
      if (kind === 'one') {
        var on = q.querySelector('input[type=radio]:checked');
        if (on) { answers[key] = cut(on.value, MAX_CHOICE); }
      } else if (kind === 'many') {
        var ticked = q.querySelectorAll('input[type=checkbox]:checked'), list = [];
        for (var j = 0; j < ticked.length; j++) { list.push(cut(ticked[j].value, MAX_CHOICE)); }
        if (list.length) { answers[key] = list; }
      } else {
        var box = q.querySelector('textarea, input');
        var v = box ? box.value.trim() : '';
        if (kind === 'follow') { follow = cut(v, MAX_FOLLOW); }
        else if (v) { answers[key] = cut(v, MAX_ANSWER); }
      }
    }
    var hp = form.querySelector('.ordpar-report-trap input');
    if (hp) { trap = hp.value; }
    return { answers: answers, follow: follow, trap: trap };
  }

  /** Hide each question whose `skip_if` answer is chosen; show it again otherwise. */
  function skip(form) {
    var qs = form.querySelectorAll('[data-skip-q]');
    for (var i = 0; i < qs.length; i++) {
      var q = qs[i];
      var on = form.querySelector('[data-q="' + q.getAttribute('data-skip-q') + '"] input:checked');
      q.hidden = !!on && on.value === q.getAttribute('data-skip-v');
    }
  }

  function wire(form) {
    if (!form || form.getAttribute('data-wired')) { return false; }
    form.setAttribute('data-wired', '');
    var status = form.querySelector('.ordpar-survey-status');
    var send = form.querySelector('.ordpar-survey-send');
    var done = doc.getElementById('ordpar-survey-done');
    var busy = false;
    function say(key, failed) {
      status.textContent = key ? t(key) : '';
      status.classList.toggle('ordpar-report-status--failed', !!failed);
    }
    form.addEventListener('change', function () { skip(form); });
    skip(form);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (busy) { return; }
      var got = collect(form);
      var any = false, k;
      for (k in got.answers) { if (Object.prototype.hasOwnProperty.call(got.answers, k)) { any = true; } }
      if (!any && !got.follow) { say('empty', true); return; }
      if (!api.SURVEY_RECEIVER || typeof global.fetch !== 'function') { say('failed', true); return; }
      if (nav.onLine === false) { say('offline', true); return; }
      busy = true;
      send.setAttribute('aria-disabled', 'true');
      say('sending');
      global.fetch(api.SURVEY_RECEIVER, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
        body: JSON.stringify(message(got.answers, got.follow, got.trap)),
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        cache: 'no-store'
      }).then(function (r) {
        if (r.ok) {
          say('');
          form.reset();
          skip(form);
          form.hidden = true;
          if (done) {
            done.textContent = t('sent');
            done.hidden = false;
            done.focus();
          }
        } else {
          say(r.status === 429 ? 'tooMany' : 'failed', true);
        }
      }, function () {
        say(nav.onLine === false ? 'offline' : 'failed', true);
      }).then(function () {
        busy = false;
        send.removeAttribute('aria-disabled');
      });
    });
    return true;
  }

  var api = {
    collect: collect,
    message: message,
    wire: wire,
    SURVEY_RECEIVER: SURVEY_RECEIVER,
    MAX_ANSWER: MAX_ANSWER,
    MAX_CHOICE: MAX_CHOICE,
    MAX_FOLLOW: MAX_FOLLOW
  };
  global.ordparSurvey = api;
  if (doc && doc.getElementById) { wire(doc.getElementById('ordpar-survey')); }
}(typeof globalThis !== 'undefined' ? globalThis : this));
