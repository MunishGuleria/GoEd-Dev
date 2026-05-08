/**
 * Chatbot Widget Bundle
 * Auto-generated - Do not edit directly
 * Generated: 2026-04-30T09:50:35.326Z
 */

// Auto-inject CSS styles
(function() {
    const style = document.createElement('style');
    style.id = 'chatbot-widget-styles';
    style.textContent = ":root{--cb-font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;--cb-font-size-base:15px;--cb-line-height:1.6;--cb-color-primary:#6366F1;--cb-color-primary-hover:#4F46E5;--cb-color-bg:#ffffff;--cb-color-bg-alt:#F8FAFC;--cb-color-text-main:#0F172A;--cb-color-text-muted:#64748B;--cb-color-border:#E2E8F0;--cb-msg-user-bg:linear-gradient(135deg,#6366F1,#8B5CF6);--cb-msg-user-text:#ffffff;--cb-msg-ai-bg:#F1F5F9;--cb-msg-ai-text:var(--cb-color-text-main);--cb-shadow-sm:0 1px 3px rgba(0,0,0,0.05);--cb-shadow-wrapper:0 25px 50px -12px rgba(0,0,0,0.15),0 8px 20px rgba(0,0,0,0.08);--cb-radius-lg:24px;--cb-radius-md:16px;--cb-radius-sm:10px;--cb-transition:all 0.25s cubic-bezier(0.2,0.8,0.2,1);}.chatbot-widget.chatbot-dark-theme{--cb-color-primary:#818CF8;--cb-color-primary-hover:#A5B4FC;--cb-color-bg:#0F172A;--cb-color-bg-alt:#1E293B;--cb-color-text-main:#F8FAFC;--cb-color-text-muted:#94A3B8;--cb-color-border:#334155;--cb-msg-ai-bg:#1E293B;--cb-msg-ai-text:#F8FAFC;--cb-shadow-wrapper:0 25px 50px -12px rgba(0,0,0,0.5),0 8px 20px rgba(0,0,0,0.3);}.chatbot-widget-container{position:fixed;bottom:30px;right:30px;z-index:214483690;font-family:var(--cb-font-family);-webkit-font-smoothing:antialiased;}.chatbot-toggle-btn{width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#6366F1,#8B5CF6);border:none;cursor:pointer;box-shadow:0 8px 24px rgba(99,102,241,0.4);transition:var(--cb-transition);display:flex;align-items:center;justify-content:center;color:white;position:absolute;bottom:0;right:0;}.chatbot-toggle-btn:hover{transform:scale(1.08) translateY(-2px);box-shadow:0 12px 32px rgba(99,102,241,0.5);}.chatbot-toggle-btn svg{width:32px;height:32px;}.chatbot-icon-open{display:block;}.chatbot-icon-close{display:none;}.chatbot-launcher-bubble{position:absolute;bottom:80px;right:0;background:white;padding:12px 20px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.12);font-size:15px;font-weight:600;color:#2D3E50;white-space:nowrap;display:flex;align-items:center;gap:12px;z-index:214483691;pointer-events:none;transition:opacity 0.3s ease,transform 0.3s ease;border:1px solid rgba(0,0,0,0.05);}.chatbot-launcher-bubble::after{content:'';position:absolute;bottom:-9px;right:22px;width:0;height:0;border-left:10px solid transparent;border-right:10px solid transparent;border-top:10px solid white;filter:drop-shadow(0 2px 2px rgba(0,0,0,0.05));}.chatbot-launcher-bubble .bubble-icon{font-size:18px;}.chatbot-launcher-bubble.hiding{opacity:0;transform:translateY(10px) scale(0.95);}.chatbot-launcher-bubble.showing{animation:bubble-slide-in 0.4s cubic-bezier(0.175,0.885,0.32,1.275);}@keyframes bubble-slide-in{from{opacity:0;transform:translateY(15px) scale(0.8);}to{opacity:1;transform:translateY(0) scale(1);}}.chatbot-widget{position:absolute;bottom:80px;right:0;width:500px;height:800px;max-height:calc(100vh - 120px);background:var(--cb-color-bg);border-radius:var(--cb-radius-lg);box-shadow:var(--cb-shadow-wrapper);display:flex;flex-direction:column;overflow:hidden;transform-origin:bottom right;animation:chatbot-scale-in 0.3s cubic-bezier(0.2,0.8,0.2,1);border:1px solid var(--cb-color-border);}@keyframes chatbot-scale-in{from{opacity:0;transform:scale(0.9) translateY(20px);}to{opacity:1;transform:scale(1) translateY(0);}}.chatbot-header{padding:20px 24px;background:var(--cb-color-primary);display:flex;align-items:center;justify-content:space-between;color:white;}.chatbot-header-content{display:flex;align-items:center;gap:14px;}.chatbot-avatar{width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,0.2);backdrop-filter:blur(10px);display:flex;align-items:center;justify-content:center;font-size:24px;}.chatbot-header-text{display:flex;flex-direction:column;}.chatbot-title{font-weight:600;font-size:17px;color:white;letter-spacing:-0.01em;}.chatbot-status{font-size:13px;color:rgba(255,255,255,0.9);display:flex;align-items:center;gap:6px;}.chatbot-status-dot{width:7px;height:7px;border-radius:50%;background:#10B981;box-shadow:0 0 0 2px rgba(16,185,129,0.2);animation:pulse 2s infinite;}@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.5;}}.chatbot-header-actions{display:flex;gap:8px;}.chatbot-header-btn{width:36px;height:36px;border-radius:var(--cb-radius-sm);background:rgba(255,255,255,0.15);border:none;color:white;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:var(--cb-transition);}.chatbot-header-btn:hover{background:rgba(255,255,255,0.25);}.chatbot-header-btn svg{width:18px;height:18px;stroke:white;}.chatbot-messages{flex:1;overflow-y:auto;padding:24px 20px;display:flex;flex-direction:column;gap:18px;background:var(--cb-color-bg);}.chatbot-messages::-webkit-scrollbar{width:6px;}.chatbot-messages::-webkit-scrollbar-thumb{background-color:var(--cb-color-border);border-radius:10px;}.chatbot-messages::-webkit-scrollbar-track{background:transparent;}.chatbot-message{display:flex;gap:12px;max-width:80%;animation:chatbot-slide-up 0.3s ease-out;position:relative;}@keyframes chatbot-slide-up{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}.chatbot-message-user{align-self:flex-end;flex-direction:row-reverse;max-width:75%;margin-left:50px;}.chatbot-message-user .chatbot-message-content{background:var(--cb-msg-user-bg);color:var(--cb-msg-user-text);border-radius:20px 20px 4px 20px;box-shadow:0 4px 14px rgba(99,102,241,0.25);}.chatbot-message-ai{align-self:flex-start;margin-right:20px;}.chatbot-message-ai .chatbot-message-bubble{display:flex;flex-direction:column;}.chatbot-message-ai .chatbot-message-content{background:var(--cb-msg-ai-bg);color:var(--cb-msg-ai-text);border-radius:20px 20px 20px 4px;box-shadow:0 2px 8px rgba(0,0,0,0.05);}.chatbot-message-content{padding:14px 18px;font-size:var(--cb-font-size-base);line-height:1.5;word-break:normal;overflow-wrap:break-word;max-width:100%;width:fit-content;}.chatbot-message-ai .chatbot-message-content p{margin:0 0 8px 0;}.chatbot-message-ai .chatbot-message-content p:last-child{margin-bottom:0;}.chatbot-message-ai .chatbot-message-content h2,.chatbot-message-ai .chatbot-message-content h3,.chatbot-message-ai .chatbot-message-content h4{margin:12px 0 6px 0;font-weight:600;line-height:1.3;color:var(--cb-color-text-main);}.chatbot-message-ai .chatbot-message-content h2{font-size:1.15em;}.chatbot-message-ai .chatbot-message-content h3{font-size:1.05em;}.chatbot-message-ai .chatbot-message-content h4{font-size:1em;}.chatbot-message-ai .chatbot-message-content ul,.chatbot-message-ai .chatbot-message-content ol{margin:6px 0 10px 0;padding-left:22px;}.chatbot-message-ai .chatbot-message-content li{margin-bottom:4px;line-height:1.5;}.chatbot-message-ai .chatbot-message-content strong{font-weight:600;}.chatbot-message-ai .chatbot-message-content em{font-style:italic;}.chatbot-message-ai .chatbot-message-content code{background:rgba(99,102,241,0.08);color:#6366F1;padding:2px 6px;border-radius:4px;font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;font-size:0.88em;}.chatbot-message-ai .chatbot-message-content pre{background:#1E293B;color:#E2E8F0;padding:12px 16px;border-radius:8px;overflow-x:auto;margin:8px 0;font-size:0.85em;line-height:1.5;}.chatbot-message-ai .chatbot-message-content pre code{background:transparent;color:inherit;padding:0;border-radius:0;font-size:inherit;}.chatbot-dark-theme .chatbot-message-ai .chatbot-message-content code{background:rgba(129,140,248,0.15);color:#A5B4FC;}.chatbot-dark-theme .chatbot-message-ai .chatbot-message-content pre{background:#0F172A;border:1px solid #334155;}.chatbot-message-avatar{width:32px;height:32px;flex-shrink:0;border-radius:50%;background:var(--cb-color-bg-alt);display:flex;align-items:center;justify-content:center;font-size:18px;}.chatbot-typing-indicator{display:flex;align-items:flex-start;gap:12px;animation:chatbot-slide-up 0.3s ease-out;}.chatbot-typing-dots{display:flex;align-items:center;gap:6px;padding:16px 20px;background:var(--cb-msg-ai-bg);border-radius:20px 20px 20px 4px;}.chatbot-typing-dots span{width:8px;height:8px;background:var(--cb-color-primary);border-radius:50%;animation:chatbot-bounce 1.4s infinite ease-in-out both;}.chatbot-typing-dots span:nth-child(1){animation-delay:-0.32s;}.chatbot-typing-dots span:nth-child(2){animation-delay:-0.16s;}@keyframes chatbot-bounce{0%,80%,100%{transform:scale(0.6);opacity:0.5;}40%{transform:scale(1);opacity:1;}}.chatbot-input-area{padding:18px 24px;background:var(--cb-color-bg);border-top:1px solid var(--cb-color-border);display:flex;align-items:center;gap:12px;}.chatbot-input{flex:1;border:1px solid var(--cb-color-border);background:var(--cb-color-bg-alt);border-radius:18px;padding:12px 16px;font-size:14px;color:var(--cb-color-text-main);outline:none;transition:border-color 0.2s;resize:none;line-height:1.5;overflow-y:hidden;min-height:44px;max-height:120px;display:block;}.chatbot-input:focus{background:var(--cb-color-bg);border-color:var(--cb-color-primary);box-shadow:0 0 0 3px rgba(99,102,241,0.1);}.chatbot-input::placeholder{color:var(--cb-color-text-muted);}.chatbot-input:disabled{background:var(--cb-color-border);color:var(--cb-color-text-muted);cursor:not-allowed;opacity:0.7;}.chatbot-send-btn{width:44px;height:44px;background:var(--cb-color-primary);border-radius:50%;border:none;color:white;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:var(--cb-transition);flex-shrink:0;}.chatbot-send-btn:hover:not(:disabled){background:var(--cb-color-primary-hover);transform:scale(1.05);}.chatbot-send-btn:disabled{background:var(--cb-color-bg-alt);color:var(--cb-color-text-muted);cursor:not-allowed;}.chatbot-send-btn svg{width:20px;height:20px;fill:white;}.chatbot-footer{padding:12px 24px;text-align:center;background:var(--cb-color-bg);border-top:1px solid var(--cb-color-border);}.chatbot-powered-by{font-size:11px;color:var(--cb-color-text-muted);letter-spacing:0.02em;}.chatbot-system-message .chatbot-message-bubble{background:#FEF2F2 !important;border-left:4px solid #EF4444 !important;}.chatbot-system-message .chatbot-message-content{background:transparent !important;color:#991B1B !important;}.chatbot-expiry-archived{background:#FEF3C7 !important;border-left:4px solid #F59E0B !important;}.chatbot-expiry-archived .chatbot-message-content{background:transparent !important;color:#92400E !important;}.chatbot-expiry-inactive{background:#FEF2F2 !important;border-left:4px solid #EF4444 !important;}.chatbot-expiry-inactive .chatbot-message-content{background:transparent !important;color:#991B1B !important;}.chatbot-error-bubble{background:#FEF2F2 !important;border:1px solid #FCA5A5 !important;}.chatbot-error-text{color:#B91C1C !important;font-weight:500;}@media (max-width:768px){.chatbot-widget-container{pointer-events:none;bottom:0 !important;right:0 !important;left:0 !important;top:0 !important;width:100% !important;height:100% !important;transition:none !important;margin:0 !important;z-index:214483690 !important;}.chatbot-toggle-btn,.chatbot-widget{pointer-events:auto;}.chatbot-widget{display:none;width:100% !important;height:100% !important;max-height:100dvh !important;bottom:0 !important;right:0 !important;left:0 !important;border-radius:0 !important;border:none !important;margin:0 !important;transform:none !important;animation:chatbot-slide-in-mobile 0.3s cubic-bezier(0.2,0.8,0.2,1);z-index:214483691 !important;}.chatbot-widget[style*=\"display:flex\"]{display:flex !important;}@keyframes chatbot-slide-in-mobile{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}.chatbot-widget-container.is-open .chatbot-toggle-btn{display:none !important;}.chatbot-toggle-btn{bottom:24px !important;right:24px !important;width:60px !important;height:60px !important;z-index:214483692 !important;}.chatbot-header{padding:16px 20px !important;border-radius:0 !important;}.chatbot-avatar{width:36px !important;height:36px !important;font-size:20px !important;}.chatbot-title{font-size:16px !important;}.chatbot-messages{padding:16px 16px !important;flex:1;}.chatbot-message-content{max-width:85% !important;padding:12px 14px !important;font-size:14px !important;}.chatbot-input-area{padding:12px 16px !important;padding-bottom:calc(12px+env(safe-area-inset-bottom,10px)) !important;background:var(--cb-color-bg);}.chatbot-input{padding:10px 16px !important;font-size:16px !important;}.chatbot-send-btn{width:44px !important;height:44px !important;}.chatbot-footer{padding:8px 20px !important;padding-bottom:calc(8px+env(safe-area-inset-bottom,5px)) !important;}}";
    document.head.appendChild(style);
})();


// ============ src/marked.min.js ============
/**
 * marked v15.0.12 - a markdown parser
 * Copyright (c) 2011-2025, Christopher Jeffrey. (MIT Licensed)
 * https://github.com/markedjs/marked
 */

/**
 * DO NOT EDIT THIS FILE
 * The code in this file is generated from files in ./src/
 */
(function(g,f){if(typeof exports=="object"&&typeof module<"u"){module.exports=f()}else if("function"==typeof define && define.amd){define("marked",f)}else {g["marked"]=f()}}(typeof globalThis < "u" ? globalThis : typeof self < "u" ? self : this,function(){var exports={};var __exports=exports;var module={exports};
"use strict";var H=Object.defineProperty;var be=Object.getOwnPropertyDescriptor;var Te=Object.getOwnPropertyNames;var we=Object.prototype.hasOwnProperty;var ye=(l,e)=>{for(var t in e)H(l,t,{get:e[t],enumerable:!0})},Re=(l,e,t,n)=>{if(e&&typeof e=="object"||typeof e=="function")for(let s of Te(e))!we.call(l,s)&&s!==t&&H(l,s,{get:()=>e[s],enumerable:!(n=be(e,s))||n.enumerable});return l};var Se=l=>Re(H({},"__esModule",{value:!0}),l);var kt={};ye(kt,{Hooks:()=>L,Lexer:()=>x,Marked:()=>E,Parser:()=>b,Renderer:()=>$,TextRenderer:()=>_,Tokenizer:()=>S,defaults:()=>w,getDefaults:()=>z,lexer:()=>ht,marked:()=>k,options:()=>it,parse:()=>pt,parseInline:()=>ct,parser:()=>ut,setOptions:()=>ot,use:()=>lt,walkTokens:()=>at});module.exports=Se(kt);function z(){return{async:!1,breaks:!1,extensions:null,gfm:!0,hooks:null,pedantic:!1,renderer:null,silent:!1,tokenizer:null,walkTokens:null}}var w=z();function N(l){w=l}var I={exec:()=>null};function h(l,e=""){let t=typeof l=="string"?l:l.source,n={replace:(s,i)=>{let r=typeof i=="string"?i:i.source;return r=r.replace(m.caret,"$1"),t=t.replace(s,r),n},getRegex:()=>new RegExp(t,e)};return n}var m={codeRemoveIndent:/^(?: {1,4}| {0,3}\t)/gm,outputLinkReplace:/\\([\[\]])/g,indentCodeCompensation:/^(\s+)(?:```)/,beginningSpace:/^\s+/,endingHash:/#$/,startingSpaceChar:/^ /,endingSpaceChar:/ $/,nonSpaceChar:/[^ ]/,newLineCharGlobal:/\n/g,tabCharGlobal:/\t/g,multipleSpaceGlobal:/\s+/g,blankLine:/^[ \t]*$/,doubleBlankLine:/\n[ \t]*\n[ \t]*$/,blockquoteStart:/^ {0,3}>/,blockquoteSetextReplace:/\n {0,3}((?:=+|-+) *)(?=\n|$)/g,blockquoteSetextReplace2:/^ {0,3}>[ \t]?/gm,listReplaceTabs:/^\t+/,listReplaceNesting:/^ {1,4}(?=( {4})*[^ ])/g,listIsTask:/^\[[ xX]\] /,listReplaceTask:/^\[[ xX]\] +/,anyLine:/\n.*\n/,hrefBrackets:/^<(.*)>$/,tableDelimiter:/[:|]/,tableAlignChars:/^\||\| *$/g,tableRowBlankLine:/\n[ \t]*$/,tableAlignRight:/^ *-+: *$/,tableAlignCenter:/^ *:-+: *$/,tableAlignLeft:/^ *:-+ *$/,startATag:/^<a /i,endATag:/^<\/a>/i,startPreScriptTag:/^<(pre|code|kbd|script)(\s|>)/i,endPreScriptTag:/^<\/(pre|code|kbd|script)(\s|>)/i,startAngleBracket:/^</,endAngleBracket:/>$/,pedanticHrefTitle:/^([^'"]*[^\s])\s+(['"])(.*)\2/,unicodeAlphaNumeric:/[\p{L}\p{N}]/u,escapeTest:/[&<>"']/,escapeReplace:/[&<>"']/g,escapeTestNoEncode:/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,escapeReplaceNoEncode:/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,unescapeTest:/&(#(?:\d+)|(?:#x[0-9A-Fa-f]+)|(?:\w+));?/ig,caret:/(^|[^\[])\^/g,percentDecode:/%25/g,findPipe:/\|/g,splitPipe:/ \|/,slashPipe:/\\\|/g,carriageReturn:/\r\n|\r/g,spaceLine:/^ +$/gm,notSpaceStart:/^\S*/,endingNewline:/\n$/,listItemRegex:l=>new RegExp(`^( {0,3}${l})((?:[	 ][^\\n]*)?(?:\\n|$))`),nextBulletRegex:l=>new RegExp(`^ {0,${Math.min(3,l-1)}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`),hrRegex:l=>new RegExp(`^ {0,${Math.min(3,l-1)}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`),fencesBeginRegex:l=>new RegExp(`^ {0,${Math.min(3,l-1)}}(?:\`\`\`|~~~)`),headingBeginRegex:l=>new RegExp(`^ {0,${Math.min(3,l-1)}}#`),htmlBeginRegex:l=>new RegExp(`^ {0,${Math.min(3,l-1)}}<(?:[a-z].*>|!--)`,"i")},$e=/^(?:[ \t]*(?:\n|$))+/,_e=/^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/,Le=/^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/,O=/^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/,ze=/^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/,F=/(?:[*+-]|\d{1,9}[.)])/,ie=/^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/,oe=h(ie).replace(/bull/g,F).replace(/blockCode/g,/(?: {4}| {0,3}\t)/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).replace(/\|table/g,"").getRegex(),Me=h(ie).replace(/bull/g,F).replace(/blockCode/g,/(?: {4}| {0,3}\t)/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).replace(/table/g,/ {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(),Q=/^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/,Pe=/^[^\n]+/,U=/(?!\s*\])(?:\\.|[^\[\]\\])+/,Ae=h(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label",U).replace("title",/(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(),Ee=h(/^( {0,3}bull)([ \t][^\n]+?)?(?:\n|$)/).replace(/bull/g,F).getRegex(),v="address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul",K=/<!--(?:-?>|[\s\S]*?(?:-->|$))/,Ce=h("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))","i").replace("comment",K).replace("tag",v).replace("attribute",/ +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(),le=h(Q).replace("hr",O).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("|lheading","").replace("|table","").replace("blockquote"," {0,3}>").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)]) ").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",v).getRegex(),Ie=h(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph",le).getRegex(),X={blockquote:Ie,code:_e,def:Ae,fences:Le,heading:ze,hr:O,html:Ce,lheading:oe,list:Ee,newline:$e,paragraph:le,table:I,text:Pe},re=h("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr",O).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("blockquote"," {0,3}>").replace("code","(?: {4}| {0,3}	)[^\\n]").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)]) ").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",v).getRegex(),Oe={...X,lheading:Me,table:re,paragraph:h(Q).replace("hr",O).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("|lheading","").replace("table",re).replace("blockquote"," {0,3}>").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)]) ").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",v).getRegex()},Be={...X,html:h(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace("comment",K).replace(/tag/g,"(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),def:/^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,heading:/^(#{1,6})(.*)(?:\n+|$)/,fences:I,lheading:/^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,paragraph:h(Q).replace("hr",O).replace("heading",` *#{1,6} *[^
]`).replace("lheading",oe).replace("|table","").replace("blockquote"," {0,3}>").replace("|fences","").replace("|list","").replace("|html","").replace("|tag","").getRegex()},qe=/^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/,ve=/^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/,ae=/^( {2,}|\\)\n(?!\s*$)/,De=/^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/,D=/[\p{P}\p{S}]/u,W=/[\s\p{P}\p{S}]/u,ce=/[^\s\p{P}\p{S}]/u,Ze=h(/^((?![*_])punctSpace)/,"u").replace(/punctSpace/g,W).getRegex(),pe=/(?!~)[\p{P}\p{S}]/u,Ge=/(?!~)[\s\p{P}\p{S}]/u,He=/(?:[^\s\p{P}\p{S}]|~)/u,Ne=/\[[^[\]]*?\]\((?:\\.|[^\\\(\)]|\((?:\\.|[^\\\(\)])*\))*\)|`[^`]*?`|<[^<>]*?>/g,ue=/^(?:\*+(?:((?!\*)punct)|[^\s*]))|^_+(?:((?!_)punct)|([^\s_]))/,je=h(ue,"u").replace(/punct/g,D).getRegex(),Fe=h(ue,"u").replace(/punct/g,pe).getRegex(),he="^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)",Qe=h(he,"gu").replace(/notPunctSpace/g,ce).replace(/punctSpace/g,W).replace(/punct/g,D).getRegex(),Ue=h(he,"gu").replace(/notPunctSpace/g,He).replace(/punctSpace/g,Ge).replace(/punct/g,pe).getRegex(),Ke=h("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)","gu").replace(/notPunctSpace/g,ce).replace(/punctSpace/g,W).replace(/punct/g,D).getRegex(),Xe=h(/\\(punct)/,"gu").replace(/punct/g,D).getRegex(),We=h(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme",/[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email",/[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(),Je=h(K).replace("(?:-->|$)","-->").getRegex(),Ve=h("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment",Je).replace("attribute",/\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(),q=/(?:\[(?:\\.|[^\[\]\\])*\]|\\.|`[^`]*`|[^\[\]\\`])*?/,Ye=h(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]*(?:\n[ \t]*)?)(title))?\s*\)/).replace("label",q).replace("href",/<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*/).replace("title",/"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(),ke=h(/^!?\[(label)\]\[(ref)\]/).replace("label",q).replace("ref",U).getRegex(),ge=h(/^!?\[(ref)\](?:\[\])?/).replace("ref",U).getRegex(),et=h("reflink|nolink(?!\\()","g").replace("reflink",ke).replace("nolink",ge).getRegex(),J={_backpedal:I,anyPunctuation:Xe,autolink:We,blockSkip:Ne,br:ae,code:ve,del:I,emStrongLDelim:je,emStrongRDelimAst:Qe,emStrongRDelimUnd:Ke,escape:qe,link:Ye,nolink:ge,punctuation:Ze,reflink:ke,reflinkSearch:et,tag:Ve,text:De,url:I},tt={...J,link:h(/^!?\[(label)\]\((.*?)\)/).replace("label",q).getRegex(),reflink:h(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label",q).getRegex()},j={...J,emStrongRDelimAst:Ue,emStrongLDelim:Fe,url:h(/^((?:ftp|https?):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/,"i").replace("email",/[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),_backpedal:/(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,del:/^(~~?)(?=[^\s~])((?:\\.|[^\\])*?(?:\\.|[^\s~\\]))\1(?=[^~]|$)/,text:/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|https?:\/\/|ftp:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/},nt={...j,br:h(ae).replace("{2,}","*").getRegex(),text:h(j.text).replace("\\b_","\\b_| {2,}\\n").replace(/\{2,\}/g,"*").getRegex()},B={normal:X,gfm:Oe,pedantic:Be},P={normal:J,gfm:j,breaks:nt,pedantic:tt};var st={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"},fe=l=>st[l];function R(l,e){if(e){if(m.escapeTest.test(l))return l.replace(m.escapeReplace,fe)}else if(m.escapeTestNoEncode.test(l))return l.replace(m.escapeReplaceNoEncode,fe);return l}function V(l){try{l=encodeURI(l).replace(m.percentDecode,"%")}catch{return null}return l}function Y(l,e){let t=l.replace(m.findPipe,(i,r,o)=>{let a=!1,c=r;for(;--c>=0&&o[c]==="\\";)a=!a;return a?"|":" |"}),n=t.split(m.splitPipe),s=0;if(n[0].trim()||n.shift(),n.length>0&&!n.at(-1)?.trim()&&n.pop(),e)if(n.length>e)n.splice(e);else for(;n.length<e;)n.push("");for(;s<n.length;s++)n[s]=n[s].trim().replace(m.slashPipe,"|");return n}function A(l,e,t){let n=l.length;if(n===0)return"";let s=0;for(;s<n;){let i=l.charAt(n-s-1);if(i===e&&!t)s++;else if(i!==e&&t)s++;else break}return l.slice(0,n-s)}function de(l,e){if(l.indexOf(e[1])===-1)return-1;let t=0;for(let n=0;n<l.length;n++)if(l[n]==="\\")n++;else if(l[n]===e[0])t++;else if(l[n]===e[1]&&(t--,t<0))return n;return t>0?-2:-1}function me(l,e,t,n,s){let i=e.href,r=e.title||null,o=l[1].replace(s.other.outputLinkReplace,"$1");n.state.inLink=!0;let a={type:l[0].charAt(0)==="!"?"image":"link",raw:t,href:i,title:r,text:o,tokens:n.inlineTokens(o)};return n.state.inLink=!1,a}function rt(l,e,t){let n=l.match(t.other.indentCodeCompensation);if(n===null)return e;let s=n[1];return e.split(`
`).map(i=>{let r=i.match(t.other.beginningSpace);if(r===null)return i;let[o]=r;return o.length>=s.length?i.slice(s.length):i}).join(`
`)}var S=class{options;rules;lexer;constructor(e){this.options=e||w}space(e){let t=this.rules.block.newline.exec(e);if(t&&t[0].length>0)return{type:"space",raw:t[0]}}code(e){let t=this.rules.block.code.exec(e);if(t){let n=t[0].replace(this.rules.other.codeRemoveIndent,"");return{type:"code",raw:t[0],codeBlockStyle:"indented",text:this.options.pedantic?n:A(n,`
`)}}}fences(e){let t=this.rules.block.fences.exec(e);if(t){let n=t[0],s=rt(n,t[3]||"",this.rules);return{type:"code",raw:n,lang:t[2]?t[2].trim().replace(this.rules.inline.anyPunctuation,"$1"):t[2],text:s}}}heading(e){let t=this.rules.block.heading.exec(e);if(t){let n=t[2].trim();if(this.rules.other.endingHash.test(n)){let s=A(n,"#");(this.options.pedantic||!s||this.rules.other.endingSpaceChar.test(s))&&(n=s.trim())}return{type:"heading",raw:t[0],depth:t[1].length,text:n,tokens:this.lexer.inline(n)}}}hr(e){let t=this.rules.block.hr.exec(e);if(t)return{type:"hr",raw:A(t[0],`
`)}}blockquote(e){let t=this.rules.block.blockquote.exec(e);if(t){let n=A(t[0],`
`).split(`
`),s="",i="",r=[];for(;n.length>0;){let o=!1,a=[],c;for(c=0;c<n.length;c++)if(this.rules.other.blockquoteStart.test(n[c]))a.push(n[c]),o=!0;else if(!o)a.push(n[c]);else break;n=n.slice(c);let p=a.join(`
`),u=p.replace(this.rules.other.blockquoteSetextReplace,`
    $1`).replace(this.rules.other.blockquoteSetextReplace2,"");s=s?`${s}
${p}`:p,i=i?`${i}
${u}`:u;let d=this.lexer.state.top;if(this.lexer.state.top=!0,this.lexer.blockTokens(u,r,!0),this.lexer.state.top=d,n.length===0)break;let g=r.at(-1);if(g?.type==="code")break;if(g?.type==="blockquote"){let T=g,f=T.raw+`
`+n.join(`
`),y=this.blockquote(f);r[r.length-1]=y,s=s.substring(0,s.length-T.raw.length)+y.raw,i=i.substring(0,i.length-T.text.length)+y.text;break}else if(g?.type==="list"){let T=g,f=T.raw+`
`+n.join(`
`),y=this.list(f);r[r.length-1]=y,s=s.substring(0,s.length-g.raw.length)+y.raw,i=i.substring(0,i.length-T.raw.length)+y.raw,n=f.substring(r.at(-1).raw.length).split(`
`);continue}}return{type:"blockquote",raw:s,tokens:r,text:i}}}list(e){let t=this.rules.block.list.exec(e);if(t){let n=t[1].trim(),s=n.length>1,i={type:"list",raw:"",ordered:s,start:s?+n.slice(0,-1):"",loose:!1,items:[]};n=s?`\\d{1,9}\\${n.slice(-1)}`:`\\${n}`,this.options.pedantic&&(n=s?n:"[*+-]");let r=this.rules.other.listItemRegex(n),o=!1;for(;e;){let c=!1,p="",u="";if(!(t=r.exec(e))||this.rules.block.hr.test(e))break;p=t[0],e=e.substring(p.length);let d=t[2].split(`
`,1)[0].replace(this.rules.other.listReplaceTabs,Z=>" ".repeat(3*Z.length)),g=e.split(`
`,1)[0],T=!d.trim(),f=0;if(this.options.pedantic?(f=2,u=d.trimStart()):T?f=t[1].length+1:(f=t[2].search(this.rules.other.nonSpaceChar),f=f>4?1:f,u=d.slice(f),f+=t[1].length),T&&this.rules.other.blankLine.test(g)&&(p+=g+`
`,e=e.substring(g.length+1),c=!0),!c){let Z=this.rules.other.nextBulletRegex(f),te=this.rules.other.hrRegex(f),ne=this.rules.other.fencesBeginRegex(f),se=this.rules.other.headingBeginRegex(f),xe=this.rules.other.htmlBeginRegex(f);for(;e;){let G=e.split(`
`,1)[0],C;if(g=G,this.options.pedantic?(g=g.replace(this.rules.other.listReplaceNesting,"  "),C=g):C=g.replace(this.rules.other.tabCharGlobal,"    "),ne.test(g)||se.test(g)||xe.test(g)||Z.test(g)||te.test(g))break;if(C.search(this.rules.other.nonSpaceChar)>=f||!g.trim())u+=`
`+C.slice(f);else{if(T||d.replace(this.rules.other.tabCharGlobal,"    ").search(this.rules.other.nonSpaceChar)>=4||ne.test(d)||se.test(d)||te.test(d))break;u+=`
`+g}!T&&!g.trim()&&(T=!0),p+=G+`
`,e=e.substring(G.length+1),d=C.slice(f)}}i.loose||(o?i.loose=!0:this.rules.other.doubleBlankLine.test(p)&&(o=!0));let y=null,ee;this.options.gfm&&(y=this.rules.other.listIsTask.exec(u),y&&(ee=y[0]!=="[ ] ",u=u.replace(this.rules.other.listReplaceTask,""))),i.items.push({type:"list_item",raw:p,task:!!y,checked:ee,loose:!1,text:u,tokens:[]}),i.raw+=p}let a=i.items.at(-1);if(a)a.raw=a.raw.trimEnd(),a.text=a.text.trimEnd();else return;i.raw=i.raw.trimEnd();for(let c=0;c<i.items.length;c++)if(this.lexer.state.top=!1,i.items[c].tokens=this.lexer.blockTokens(i.items[c].text,[]),!i.loose){let p=i.items[c].tokens.filter(d=>d.type==="space"),u=p.length>0&&p.some(d=>this.rules.other.anyLine.test(d.raw));i.loose=u}if(i.loose)for(let c=0;c<i.items.length;c++)i.items[c].loose=!0;return i}}html(e){let t=this.rules.block.html.exec(e);if(t)return{type:"html",block:!0,raw:t[0],pre:t[1]==="pre"||t[1]==="script"||t[1]==="style",text:t[0]}}def(e){let t=this.rules.block.def.exec(e);if(t){let n=t[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal," "),s=t[2]?t[2].replace(this.rules.other.hrefBrackets,"$1").replace(this.rules.inline.anyPunctuation,"$1"):"",i=t[3]?t[3].substring(1,t[3].length-1).replace(this.rules.inline.anyPunctuation,"$1"):t[3];return{type:"def",tag:n,raw:t[0],href:s,title:i}}}table(e){let t=this.rules.block.table.exec(e);if(!t||!this.rules.other.tableDelimiter.test(t[2]))return;let n=Y(t[1]),s=t[2].replace(this.rules.other.tableAlignChars,"").split("|"),i=t[3]?.trim()?t[3].replace(this.rules.other.tableRowBlankLine,"").split(`
`):[],r={type:"table",raw:t[0],header:[],align:[],rows:[]};if(n.length===s.length){for(let o of s)this.rules.other.tableAlignRight.test(o)?r.align.push("right"):this.rules.other.tableAlignCenter.test(o)?r.align.push("center"):this.rules.other.tableAlignLeft.test(o)?r.align.push("left"):r.align.push(null);for(let o=0;o<n.length;o++)r.header.push({text:n[o],tokens:this.lexer.inline(n[o]),header:!0,align:r.align[o]});for(let o of i)r.rows.push(Y(o,r.header.length).map((a,c)=>({text:a,tokens:this.lexer.inline(a),header:!1,align:r.align[c]})));return r}}lheading(e){let t=this.rules.block.lheading.exec(e);if(t)return{type:"heading",raw:t[0],depth:t[2].charAt(0)==="="?1:2,text:t[1],tokens:this.lexer.inline(t[1])}}paragraph(e){let t=this.rules.block.paragraph.exec(e);if(t){let n=t[1].charAt(t[1].length-1)===`
`?t[1].slice(0,-1):t[1];return{type:"paragraph",raw:t[0],text:n,tokens:this.lexer.inline(n)}}}text(e){let t=this.rules.block.text.exec(e);if(t)return{type:"text",raw:t[0],text:t[0],tokens:this.lexer.inline(t[0])}}escape(e){let t=this.rules.inline.escape.exec(e);if(t)return{type:"escape",raw:t[0],text:t[1]}}tag(e){let t=this.rules.inline.tag.exec(e);if(t)return!this.lexer.state.inLink&&this.rules.other.startATag.test(t[0])?this.lexer.state.inLink=!0:this.lexer.state.inLink&&this.rules.other.endATag.test(t[0])&&(this.lexer.state.inLink=!1),!this.lexer.state.inRawBlock&&this.rules.other.startPreScriptTag.test(t[0])?this.lexer.state.inRawBlock=!0:this.lexer.state.inRawBlock&&this.rules.other.endPreScriptTag.test(t[0])&&(this.lexer.state.inRawBlock=!1),{type:"html",raw:t[0],inLink:this.lexer.state.inLink,inRawBlock:this.lexer.state.inRawBlock,block:!1,text:t[0]}}link(e){let t=this.rules.inline.link.exec(e);if(t){let n=t[2].trim();if(!this.options.pedantic&&this.rules.other.startAngleBracket.test(n)){if(!this.rules.other.endAngleBracket.test(n))return;let r=A(n.slice(0,-1),"\\");if((n.length-r.length)%2===0)return}else{let r=de(t[2],"()");if(r===-2)return;if(r>-1){let a=(t[0].indexOf("!")===0?5:4)+t[1].length+r;t[2]=t[2].substring(0,r),t[0]=t[0].substring(0,a).trim(),t[3]=""}}let s=t[2],i="";if(this.options.pedantic){let r=this.rules.other.pedanticHrefTitle.exec(s);r&&(s=r[1],i=r[3])}else i=t[3]?t[3].slice(1,-1):"";return s=s.trim(),this.rules.other.startAngleBracket.test(s)&&(this.options.pedantic&&!this.rules.other.endAngleBracket.test(n)?s=s.slice(1):s=s.slice(1,-1)),me(t,{href:s&&s.replace(this.rules.inline.anyPunctuation,"$1"),title:i&&i.replace(this.rules.inline.anyPunctuation,"$1")},t[0],this.lexer,this.rules)}}reflink(e,t){let n;if((n=this.rules.inline.reflink.exec(e))||(n=this.rules.inline.nolink.exec(e))){let s=(n[2]||n[1]).replace(this.rules.other.multipleSpaceGlobal," "),i=t[s.toLowerCase()];if(!i){let r=n[0].charAt(0);return{type:"text",raw:r,text:r}}return me(n,i,n[0],this.lexer,this.rules)}}emStrong(e,t,n=""){let s=this.rules.inline.emStrongLDelim.exec(e);if(!s||s[3]&&n.match(this.rules.other.unicodeAlphaNumeric))return;if(!(s[1]||s[2]||"")||!n||this.rules.inline.punctuation.exec(n)){let r=[...s[0]].length-1,o,a,c=r,p=0,u=s[0][0]==="*"?this.rules.inline.emStrongRDelimAst:this.rules.inline.emStrongRDelimUnd;for(u.lastIndex=0,t=t.slice(-1*e.length+r);(s=u.exec(t))!=null;){if(o=s[1]||s[2]||s[3]||s[4]||s[5]||s[6],!o)continue;if(a=[...o].length,s[3]||s[4]){c+=a;continue}else if((s[5]||s[6])&&r%3&&!((r+a)%3)){p+=a;continue}if(c-=a,c>0)continue;a=Math.min(a,a+c+p);let d=[...s[0]][0].length,g=e.slice(0,r+s.index+d+a);if(Math.min(r,a)%2){let f=g.slice(1,-1);return{type:"em",raw:g,text:f,tokens:this.lexer.inlineTokens(f)}}let T=g.slice(2,-2);return{type:"strong",raw:g,text:T,tokens:this.lexer.inlineTokens(T)}}}}codespan(e){let t=this.rules.inline.code.exec(e);if(t){let n=t[2].replace(this.rules.other.newLineCharGlobal," "),s=this.rules.other.nonSpaceChar.test(n),i=this.rules.other.startingSpaceChar.test(n)&&this.rules.other.endingSpaceChar.test(n);return s&&i&&(n=n.substring(1,n.length-1)),{type:"codespan",raw:t[0],text:n}}}br(e){let t=this.rules.inline.br.exec(e);if(t)return{type:"br",raw:t[0]}}del(e){let t=this.rules.inline.del.exec(e);if(t)return{type:"del",raw:t[0],text:t[2],tokens:this.lexer.inlineTokens(t[2])}}autolink(e){let t=this.rules.inline.autolink.exec(e);if(t){let n,s;return t[2]==="@"?(n=t[1],s="mailto:"+n):(n=t[1],s=n),{type:"link",raw:t[0],text:n,href:s,tokens:[{type:"text",raw:n,text:n}]}}}url(e){let t;if(t=this.rules.inline.url.exec(e)){let n,s;if(t[2]==="@")n=t[0],s="mailto:"+n;else{let i;do i=t[0],t[0]=this.rules.inline._backpedal.exec(t[0])?.[0]??"";while(i!==t[0]);n=t[0],t[1]==="www."?s="http://"+t[0]:s=t[0]}return{type:"link",raw:t[0],text:n,href:s,tokens:[{type:"text",raw:n,text:n}]}}}inlineText(e){let t=this.rules.inline.text.exec(e);if(t){let n=this.lexer.state.inRawBlock;return{type:"text",raw:t[0],text:t[0],escaped:n}}}};var x=class l{tokens;options;state;tokenizer;inlineQueue;constructor(e){this.tokens=[],this.tokens.links=Object.create(null),this.options=e||w,this.options.tokenizer=this.options.tokenizer||new S,this.tokenizer=this.options.tokenizer,this.tokenizer.options=this.options,this.tokenizer.lexer=this,this.inlineQueue=[],this.state={inLink:!1,inRawBlock:!1,top:!0};let t={other:m,block:B.normal,inline:P.normal};this.options.pedantic?(t.block=B.pedantic,t.inline=P.pedantic):this.options.gfm&&(t.block=B.gfm,this.options.breaks?t.inline=P.breaks:t.inline=P.gfm),this.tokenizer.rules=t}static get rules(){return{block:B,inline:P}}static lex(e,t){return new l(t).lex(e)}static lexInline(e,t){return new l(t).inlineTokens(e)}lex(e){e=e.replace(m.carriageReturn,`
`),this.blockTokens(e,this.tokens);for(let t=0;t<this.inlineQueue.length;t++){let n=this.inlineQueue[t];this.inlineTokens(n.src,n.tokens)}return this.inlineQueue=[],this.tokens}blockTokens(e,t=[],n=!1){for(this.options.pedantic&&(e=e.replace(m.tabCharGlobal,"    ").replace(m.spaceLine,""));e;){let s;if(this.options.extensions?.block?.some(r=>(s=r.call({lexer:this},e,t))?(e=e.substring(s.raw.length),t.push(s),!0):!1))continue;if(s=this.tokenizer.space(e)){e=e.substring(s.raw.length);let r=t.at(-1);s.raw.length===1&&r!==void 0?r.raw+=`
`:t.push(s);continue}if(s=this.tokenizer.code(e)){e=e.substring(s.raw.length);let r=t.at(-1);r?.type==="paragraph"||r?.type==="text"?(r.raw+=`
`+s.raw,r.text+=`
`+s.text,this.inlineQueue.at(-1).src=r.text):t.push(s);continue}if(s=this.tokenizer.fences(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.heading(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.hr(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.blockquote(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.list(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.html(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.def(e)){e=e.substring(s.raw.length);let r=t.at(-1);r?.type==="paragraph"||r?.type==="text"?(r.raw+=`
`+s.raw,r.text+=`
`+s.raw,this.inlineQueue.at(-1).src=r.text):this.tokens.links[s.tag]||(this.tokens.links[s.tag]={href:s.href,title:s.title});continue}if(s=this.tokenizer.table(e)){e=e.substring(s.raw.length),t.push(s);continue}if(s=this.tokenizer.lheading(e)){e=e.substring(s.raw.length),t.push(s);continue}let i=e;if(this.options.extensions?.startBlock){let r=1/0,o=e.slice(1),a;this.options.extensions.startBlock.forEach(c=>{a=c.call({lexer:this},o),typeof a=="number"&&a>=0&&(r=Math.min(r,a))}),r<1/0&&r>=0&&(i=e.substring(0,r+1))}if(this.state.top&&(s=this.tokenizer.paragraph(i))){let r=t.at(-1);n&&r?.type==="paragraph"?(r.raw+=`
`+s.raw,r.text+=`
`+s.text,this.inlineQueue.pop(),this.inlineQueue.at(-1).src=r.text):t.push(s),n=i.length!==e.length,e=e.substring(s.raw.length);continue}if(s=this.tokenizer.text(e)){e=e.substring(s.raw.length);let r=t.at(-1);r?.type==="text"?(r.raw+=`
`+s.raw,r.text+=`
`+s.text,this.inlineQueue.pop(),this.inlineQueue.at(-1).src=r.text):t.push(s);continue}if(e){let r="Infinite loop on byte: "+e.charCodeAt(0);if(this.options.silent){console.error(r);break}else throw new Error(r)}}return this.state.top=!0,t}inline(e,t=[]){return this.inlineQueue.push({src:e,tokens:t}),t}inlineTokens(e,t=[]){let n=e,s=null;if(this.tokens.links){let o=Object.keys(this.tokens.links);if(o.length>0)for(;(s=this.tokenizer.rules.inline.reflinkSearch.exec(n))!=null;)o.includes(s[0].slice(s[0].lastIndexOf("[")+1,-1))&&(n=n.slice(0,s.index)+"["+"a".repeat(s[0].length-2)+"]"+n.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex))}for(;(s=this.tokenizer.rules.inline.anyPunctuation.exec(n))!=null;)n=n.slice(0,s.index)+"++"+n.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);for(;(s=this.tokenizer.rules.inline.blockSkip.exec(n))!=null;)n=n.slice(0,s.index)+"["+"a".repeat(s[0].length-2)+"]"+n.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);let i=!1,r="";for(;e;){i||(r=""),i=!1;let o;if(this.options.extensions?.inline?.some(c=>(o=c.call({lexer:this},e,t))?(e=e.substring(o.raw.length),t.push(o),!0):!1))continue;if(o=this.tokenizer.escape(e)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.tag(e)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.link(e)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.reflink(e,this.tokens.links)){e=e.substring(o.raw.length);let c=t.at(-1);o.type==="text"&&c?.type==="text"?(c.raw+=o.raw,c.text+=o.text):t.push(o);continue}if(o=this.tokenizer.emStrong(e,n,r)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.codespan(e)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.br(e)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.del(e)){e=e.substring(o.raw.length),t.push(o);continue}if(o=this.tokenizer.autolink(e)){e=e.substring(o.raw.length),t.push(o);continue}if(!this.state.inLink&&(o=this.tokenizer.url(e))){e=e.substring(o.raw.length),t.push(o);continue}let a=e;if(this.options.extensions?.startInline){let c=1/0,p=e.slice(1),u;this.options.extensions.startInline.forEach(d=>{u=d.call({lexer:this},p),typeof u=="number"&&u>=0&&(c=Math.min(c,u))}),c<1/0&&c>=0&&(a=e.substring(0,c+1))}if(o=this.tokenizer.inlineText(a)){e=e.substring(o.raw.length),o.raw.slice(-1)!=="_"&&(r=o.raw.slice(-1)),i=!0;let c=t.at(-1);c?.type==="text"?(c.raw+=o.raw,c.text+=o.text):t.push(o);continue}if(e){let c="Infinite loop on byte: "+e.charCodeAt(0);if(this.options.silent){console.error(c);break}else throw new Error(c)}}return t}};var $=class{options;parser;constructor(e){this.options=e||w}space(e){return""}code({text:e,lang:t,escaped:n}){let s=(t||"").match(m.notSpaceStart)?.[0],i=e.replace(m.endingNewline,"")+`
`;return s?'<pre><code class="language-'+R(s)+'">'+(n?i:R(i,!0))+`</code></pre>
`:"<pre><code>"+(n?i:R(i,!0))+`</code></pre>
`}blockquote({tokens:e}){return`<blockquote>
${this.parser.parse(e)}</blockquote>
`}html({text:e}){return e}heading({tokens:e,depth:t}){return`<h${t}>${this.parser.parseInline(e)}</h${t}>
`}hr(e){return`<hr>
`}list(e){let t=e.ordered,n=e.start,s="";for(let o=0;o<e.items.length;o++){let a=e.items[o];s+=this.listitem(a)}let i=t?"ol":"ul",r=t&&n!==1?' start="'+n+'"':"";return"<"+i+r+`>
`+s+"</"+i+`>
`}listitem(e){let t="";if(e.task){let n=this.checkbox({checked:!!e.checked});e.loose?e.tokens[0]?.type==="paragraph"?(e.tokens[0].text=n+" "+e.tokens[0].text,e.tokens[0].tokens&&e.tokens[0].tokens.length>0&&e.tokens[0].tokens[0].type==="text"&&(e.tokens[0].tokens[0].text=n+" "+R(e.tokens[0].tokens[0].text),e.tokens[0].tokens[0].escaped=!0)):e.tokens.unshift({type:"text",raw:n+" ",text:n+" ",escaped:!0}):t+=n+" "}return t+=this.parser.parse(e.tokens,!!e.loose),`<li>${t}</li>
`}checkbox({checked:e}){return"<input "+(e?'checked="" ':"")+'disabled="" type="checkbox">'}paragraph({tokens:e}){return`<p>${this.parser.parseInline(e)}</p>
`}table(e){let t="",n="";for(let i=0;i<e.header.length;i++)n+=this.tablecell(e.header[i]);t+=this.tablerow({text:n});let s="";for(let i=0;i<e.rows.length;i++){let r=e.rows[i];n="";for(let o=0;o<r.length;o++)n+=this.tablecell(r[o]);s+=this.tablerow({text:n})}return s&&(s=`<tbody>${s}</tbody>`),`<table>
<thead>
`+t+`</thead>
`+s+`</table>
`}tablerow({text:e}){return`<tr>
${e}</tr>
`}tablecell(e){let t=this.parser.parseInline(e.tokens),n=e.header?"th":"td";return(e.align?`<${n} align="${e.align}">`:`<${n}>`)+t+`</${n}>
`}strong({tokens:e}){return`<strong>${this.parser.parseInline(e)}</strong>`}em({tokens:e}){return`<em>${this.parser.parseInline(e)}</em>`}codespan({text:e}){return`<code>${R(e,!0)}</code>`}br(e){return"<br>"}del({tokens:e}){return`<del>${this.parser.parseInline(e)}</del>`}link({href:e,title:t,tokens:n}){let s=this.parser.parseInline(n),i=V(e);if(i===null)return s;e=i;let r='<a href="'+e+'"';return t&&(r+=' title="'+R(t)+'"'),r+=">"+s+"</a>",r}image({href:e,title:t,text:n,tokens:s}){s&&(n=this.parser.parseInline(s,this.parser.textRenderer));let i=V(e);if(i===null)return R(n);e=i;let r=`<img src="${e}" alt="${n}"`;return t&&(r+=` title="${R(t)}"`),r+=">",r}text(e){return"tokens"in e&&e.tokens?this.parser.parseInline(e.tokens):"escaped"in e&&e.escaped?e.text:R(e.text)}};var _=class{strong({text:e}){return e}em({text:e}){return e}codespan({text:e}){return e}del({text:e}){return e}html({text:e}){return e}text({text:e}){return e}link({text:e}){return""+e}image({text:e}){return""+e}br(){return""}};var b=class l{options;renderer;textRenderer;constructor(e){this.options=e||w,this.options.renderer=this.options.renderer||new $,this.renderer=this.options.renderer,this.renderer.options=this.options,this.renderer.parser=this,this.textRenderer=new _}static parse(e,t){return new l(t).parse(e)}static parseInline(e,t){return new l(t).parseInline(e)}parse(e,t=!0){let n="";for(let s=0;s<e.length;s++){let i=e[s];if(this.options.extensions?.renderers?.[i.type]){let o=i,a=this.options.extensions.renderers[o.type].call({parser:this},o);if(a!==!1||!["space","hr","heading","code","table","blockquote","list","html","paragraph","text"].includes(o.type)){n+=a||"";continue}}let r=i;switch(r.type){case"space":{n+=this.renderer.space(r);continue}case"hr":{n+=this.renderer.hr(r);continue}case"heading":{n+=this.renderer.heading(r);continue}case"code":{n+=this.renderer.code(r);continue}case"table":{n+=this.renderer.table(r);continue}case"blockquote":{n+=this.renderer.blockquote(r);continue}case"list":{n+=this.renderer.list(r);continue}case"html":{n+=this.renderer.html(r);continue}case"paragraph":{n+=this.renderer.paragraph(r);continue}case"text":{let o=r,a=this.renderer.text(o);for(;s+1<e.length&&e[s+1].type==="text";)o=e[++s],a+=`
`+this.renderer.text(o);t?n+=this.renderer.paragraph({type:"paragraph",raw:a,text:a,tokens:[{type:"text",raw:a,text:a,escaped:!0}]}):n+=a;continue}default:{let o='Token with "'+r.type+'" type was not found.';if(this.options.silent)return console.error(o),"";throw new Error(o)}}}return n}parseInline(e,t=this.renderer){let n="";for(let s=0;s<e.length;s++){let i=e[s];if(this.options.extensions?.renderers?.[i.type]){let o=this.options.extensions.renderers[i.type].call({parser:this},i);if(o!==!1||!["escape","html","link","image","strong","em","codespan","br","del","text"].includes(i.type)){n+=o||"";continue}}let r=i;switch(r.type){case"escape":{n+=t.text(r);break}case"html":{n+=t.html(r);break}case"link":{n+=t.link(r);break}case"image":{n+=t.image(r);break}case"strong":{n+=t.strong(r);break}case"em":{n+=t.em(r);break}case"codespan":{n+=t.codespan(r);break}case"br":{n+=t.br(r);break}case"del":{n+=t.del(r);break}case"text":{n+=t.text(r);break}default:{let o='Token with "'+r.type+'" type was not found.';if(this.options.silent)return console.error(o),"";throw new Error(o)}}}return n}};var L=class{options;block;constructor(e){this.options=e||w}static passThroughHooks=new Set(["preprocess","postprocess","processAllTokens"]);preprocess(e){return e}postprocess(e){return e}processAllTokens(e){return e}provideLexer(){return this.block?x.lex:x.lexInline}provideParser(){return this.block?b.parse:b.parseInline}};var E=class{defaults=z();options=this.setOptions;parse=this.parseMarkdown(!0);parseInline=this.parseMarkdown(!1);Parser=b;Renderer=$;TextRenderer=_;Lexer=x;Tokenizer=S;Hooks=L;constructor(...e){this.use(...e)}walkTokens(e,t){let n=[];for(let s of e)switch(n=n.concat(t.call(this,s)),s.type){case"table":{let i=s;for(let r of i.header)n=n.concat(this.walkTokens(r.tokens,t));for(let r of i.rows)for(let o of r)n=n.concat(this.walkTokens(o.tokens,t));break}case"list":{let i=s;n=n.concat(this.walkTokens(i.items,t));break}default:{let i=s;this.defaults.extensions?.childTokens?.[i.type]?this.defaults.extensions.childTokens[i.type].forEach(r=>{let o=i[r].flat(1/0);n=n.concat(this.walkTokens(o,t))}):i.tokens&&(n=n.concat(this.walkTokens(i.tokens,t)))}}return n}use(...e){let t=this.defaults.extensions||{renderers:{},childTokens:{}};return e.forEach(n=>{let s={...n};if(s.async=this.defaults.async||s.async||!1,n.extensions&&(n.extensions.forEach(i=>{if(!i.name)throw new Error("extension name required");if("renderer"in i){let r=t.renderers[i.name];r?t.renderers[i.name]=function(...o){let a=i.renderer.apply(this,o);return a===!1&&(a=r.apply(this,o)),a}:t.renderers[i.name]=i.renderer}if("tokenizer"in i){if(!i.level||i.level!=="block"&&i.level!=="inline")throw new Error("extension level must be 'block' or 'inline'");let r=t[i.level];r?r.unshift(i.tokenizer):t[i.level]=[i.tokenizer],i.start&&(i.level==="block"?t.startBlock?t.startBlock.push(i.start):t.startBlock=[i.start]:i.level==="inline"&&(t.startInline?t.startInline.push(i.start):t.startInline=[i.start]))}"childTokens"in i&&i.childTokens&&(t.childTokens[i.name]=i.childTokens)}),s.extensions=t),n.renderer){let i=this.defaults.renderer||new $(this.defaults);for(let r in n.renderer){if(!(r in i))throw new Error(`renderer '${r}' does not exist`);if(["options","parser"].includes(r))continue;let o=r,a=n.renderer[o],c=i[o];i[o]=(...p)=>{let u=a.apply(i,p);return u===!1&&(u=c.apply(i,p)),u||""}}s.renderer=i}if(n.tokenizer){let i=this.defaults.tokenizer||new S(this.defaults);for(let r in n.tokenizer){if(!(r in i))throw new Error(`tokenizer '${r}' does not exist`);if(["options","rules","lexer"].includes(r))continue;let o=r,a=n.tokenizer[o],c=i[o];i[o]=(...p)=>{let u=a.apply(i,p);return u===!1&&(u=c.apply(i,p)),u}}s.tokenizer=i}if(n.hooks){let i=this.defaults.hooks||new L;for(let r in n.hooks){if(!(r in i))throw new Error(`hook '${r}' does not exist`);if(["options","block"].includes(r))continue;let o=r,a=n.hooks[o],c=i[o];L.passThroughHooks.has(r)?i[o]=p=>{if(this.defaults.async)return Promise.resolve(a.call(i,p)).then(d=>c.call(i,d));let u=a.call(i,p);return c.call(i,u)}:i[o]=(...p)=>{let u=a.apply(i,p);return u===!1&&(u=c.apply(i,p)),u}}s.hooks=i}if(n.walkTokens){let i=this.defaults.walkTokens,r=n.walkTokens;s.walkTokens=function(o){let a=[];return a.push(r.call(this,o)),i&&(a=a.concat(i.call(this,o))),a}}this.defaults={...this.defaults,...s}}),this}setOptions(e){return this.defaults={...this.defaults,...e},this}lexer(e,t){return x.lex(e,t??this.defaults)}parser(e,t){return b.parse(e,t??this.defaults)}parseMarkdown(e){return(n,s)=>{let i={...s},r={...this.defaults,...i},o=this.onError(!!r.silent,!!r.async);if(this.defaults.async===!0&&i.async===!1)return o(new Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));if(typeof n>"u"||n===null)return o(new Error("marked(): input parameter is undefined or null"));if(typeof n!="string")return o(new Error("marked(): input parameter is of type "+Object.prototype.toString.call(n)+", string expected"));r.hooks&&(r.hooks.options=r,r.hooks.block=e);let a=r.hooks?r.hooks.provideLexer():e?x.lex:x.lexInline,c=r.hooks?r.hooks.provideParser():e?b.parse:b.parseInline;if(r.async)return Promise.resolve(r.hooks?r.hooks.preprocess(n):n).then(p=>a(p,r)).then(p=>r.hooks?r.hooks.processAllTokens(p):p).then(p=>r.walkTokens?Promise.all(this.walkTokens(p,r.walkTokens)).then(()=>p):p).then(p=>c(p,r)).then(p=>r.hooks?r.hooks.postprocess(p):p).catch(o);try{r.hooks&&(n=r.hooks.preprocess(n));let p=a(n,r);r.hooks&&(p=r.hooks.processAllTokens(p)),r.walkTokens&&this.walkTokens(p,r.walkTokens);let u=c(p,r);return r.hooks&&(u=r.hooks.postprocess(u)),u}catch(p){return o(p)}}}onError(e,t){return n=>{if(n.message+=`
Please report this to https://github.com/markedjs/marked.`,e){let s="<p>An error occurred:</p><pre>"+R(n.message+"",!0)+"</pre>";return t?Promise.resolve(s):s}if(t)return Promise.reject(n);throw n}}};var M=new E;function k(l,e){return M.parse(l,e)}k.options=k.setOptions=function(l){return M.setOptions(l),k.defaults=M.defaults,N(k.defaults),k};k.getDefaults=z;k.defaults=w;k.use=function(...l){return M.use(...l),k.defaults=M.defaults,N(k.defaults),k};k.walkTokens=function(l,e){return M.walkTokens(l,e)};k.parseInline=M.parseInline;k.Parser=b;k.parser=b.parse;k.Renderer=$;k.TextRenderer=_;k.Lexer=x;k.lexer=x.lex;k.Tokenizer=S;k.Hooks=L;k.parse=k;var it=k.options,ot=k.setOptions,lt=k.use,at=k.walkTokens,ct=k.parseInline,pt=k,ut=b.parse,ht=x.lex;

if(__exports != exports)module.exports = exports;return module.exports}));

// ============ env.js ============
/**
 * Runtime Configuration for Chatbot Widget
 * 
 * IMPORTANT: This file can be edited AFTER deployment without rebuilding!
 * Simply edit the values below and changes take effect on page refresh.
 * 
 * This is useful for:
 * - Changing API URL when moving between environments
 * - Updating theme colors
 * - Modifying default messages
 * - Adjusting session settings
 */

window.CHATBOT_ENV = {
    // Backend API URL - Injected by GitHub Actions from secrets.CHATBOT_API_URL
    // Production: https://zx-edu-ai.centralindia.cloudapp.azure.com/chatbot
    // Auto-detects: /chatbot on current origin in production, localhost:8000 for local dev
    API_URL: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ? 'http://localhost:8000' : (window.location.origin + '/chatbot'),

    // Session Configuration
    SESSION_EXPIRY_DAYS: 7,
    SESSION_STORAGE_KEY: 'chatbot_session',

    // UI Theme
    PRIMARY_COLOR: '#667eea',
    THEME: 'light', // 'light' or 'dark'
    WIDGET_POSITION: 'bottom-right', // 'bottom-right' or 'bottom-left'

    // Widget Dimensions
    WIDGET_WIDTH: '500px',
    WIDGET_HEIGHT: '800px',

    // Messages
    GREETING_MESSAGE: 'Hi! How can I help you today?',
    PLACEHOLDER_TEXT: 'Type your message...',
};

// ============ src/config.js ============
/**
 * Configuration for the Chatbot Widget
 * 
 * Uses runtime environment variables from window.CHATBOT_ENV (defined in env.js)
 * Falls back to defaults if env.js is not loaded
 */

const DEFAULT_CONFIG = {
    // Backend API - From runtime env or default
    apiUrl: window.CHATBOT_ENV?.API_URL || 'http://localhost:8000',

    // Session management
    sessionExpiryDays: window.CHATBOT_ENV?.SESSION_EXPIRY_DAYS || 7,
    sessionStorageKey: window.CHATBOT_ENV?.SESSION_STORAGE_KEY || 'chatbot_session',

    // UI/UX
    position: window.CHATBOT_ENV?.WIDGET_POSITION || 'bottom-right',
    primaryColor: window.CHATBOT_ENV?.PRIMARY_COLOR || '#667eea',
    theme: window.CHATBOT_ENV?.THEME || 'light',

    // Messages
    placeholder: window.CHATBOT_ENV?.PLACEHOLDER_TEXT || 'Type your message...',
    greeting: window.CHATBOT_ENV?.GREETING_MESSAGE || 'Hi! How can I help you today?',

    // Widget dimensions
    width: window.CHATBOT_ENV?.WIDGET_WIDTH || '500px',
    height: window.CHATBOT_ENV?.WIDGET_HEIGHT || '800px',

    // Launcher Bubble Messages
    launcherMessages: window.CHATBOT_ENV?.LAUNCHER_MESSAGES || [
        "Hey! Need help with admissions?",
        "Have questions about courses?",
        "Chat with Go Ed AI Assistant!"
    ],
    launcherInterval: window.CHATBOT_ENV?.LAUNCHER_INTERVAL || 5000,

    // Position Offsets
    x: window.CHATBOT_ENV?.WIDGET_X || 0,
    y: window.CHATBOT_ENV?.WIDGET_Y || 0,
};

// Export for use in other modules
window.ChatbotConfig = DEFAULT_CONFIG;

// ============ src/debug-logger.js ============
/**
 * DebugLogger - Centralized logging system for developer debugging
 * Captures all logs in memory instead of browser console
 */

class DebugLogger {
    constructor() {
        this.logs = [];
        this.maxLogs = 500; // Keep last 500 logs
    }

    /**
     * Add a log entry
     */
    _addLog(level, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message,
            data: data ? JSON.stringify(data) : null
        };

        this.logs.push(logEntry);

        // Keep only last maxLogs entries
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        // Also log to console in development (can be disabled in production)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            // Optionally keep console logs for localhost development
            // Comment out these lines to completely hide console logs
            // const consoleMethod = level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;
            // consoleMethod(`[${level.toUpperCase()}]`, message, data || '');
        }
    }

    /**
     * Log info message
     */
    log(message, data = null) {
        this._addLog('info', message, data);
    }

    /**
     * Log info message (alias)
     */
    info(message, data = null) {
        this._addLog('info', message, data);
    }

    /**
     * Log warning message
     */
    warn(message, data = null) {
        this._addLog('warn', message, data);
    }

    /**
     * Log error message
     */
    error(message, data = null) {
        this._addLog('error', message, data);
    }

    /**
     * Get all logs
     */
    getLogs() {
        return [...this.logs]; // Return copy
    }

    /**
     * Clear all logs
     */
    clearLogs() {
        this.logs = [];
    }

    /**
     * Get logs as formatted HTML
     */
    getLogsHTML() {
        return this.logs.map(log => {
            const levelColors = {
                info: '#3B82F6',
                warn: '#F59E0B',
                error: '#EF4444'
            };
            const color = levelColors[log.level] || '#6B7280';
            const time = new Date(log.timestamp).toLocaleTimeString();
            
            return `
                <div class="log-entry log-${log.level}">
                    <span class="log-time">${time}</span>
                    <span class="log-level" style="color: ${color}">[${log.level.toUpperCase()}]</span>
                    <span class="log-message">${log.message}</span>
                    ${log.data ? `<span class="log-data">${log.data}</span>` : ''}
                </div>
            `;
        }).join('');
    }
}

// Create global instance
window.DebugLogger = new DebugLogger();

// ============ src/session-manager.js ============
/**
 * SessionManager - Handles localStorage-based session persistence
 * Manages session_id, lead_id, and expiry logic
 * 
 * IMPORTANT: Session is cached in memory to prevent regenerating session_id on every call
 */

class SessionManager {
    constructor(config) {
        // Namespace the storage key so different widgets do not share sessions
        this.storageKey = config.sessionStorageKey || 'go_ed_ai_chatbot_session';
        this.expiryDays = config.expiryDays;
        this._cachedSession = null; // In-memory cache to prevent repeated regeneration
    }

    /**
     * Generate a unique session ID using Web Crypto API
     * Format: sess_<uuid>
     */
    generateSessionId() {
        return `sess_${crypto.randomUUID()}`;
    }

    /**
     * Get or create session data (with caching)
     * Returns: { session_id, lead_id, phone, email, name, created_at, last_activity, isReturning }
     *
     * NOTE: lead_id is carried forward from localStorage ONLY as a hint for the backend.
     * The backend (initSession) is responsible for validating the lead still exists.
     * If the backend marks the lead as invalid, clearLeadId() should be called.
     */
    getOrCreateSession() {
        // Return cached session if available
        if (this._cachedSession) {
            return this._cachedSession;
        }

        const stored = localStorage.getItem(this.storageKey);

        if (stored) {
            try {
                const data = JSON.parse(stored);

                // Check if expired
                const lastActivity = new Date(data.last_activity);
                const now = new Date();
                const daysSinceActivity = (now - lastActivity) / (1000 * 60 * 60 * 24);

                if (daysSinceActivity > this.expiryDays) {
                    window.DebugLogger.log('Session expired, creating new session');
                    localStorage.removeItem(this.storageKey);
                    return this._createNewSession();
                }

                // Returning user — new session_id per page load, lead_id carried forward
                // lead_id is treated as UNVERIFIED until initSession confirms it
                const isReturning = data.lead_id !== null;
                const newSession = {
                    ...data,
                    session_id: this.generateSessionId(),
                    last_activity: now.toISOString(),
                    isReturning: isReturning,
                    contactProvidedInSession: false,
                    leadVerified: false, // ← reset verification on every new page load
                };

                this._cachedSession = newSession;
                this._saveToStorage(newSession);

                if (isReturning) {
                    window.DebugLogger.log('Returning user detected, lead_id (unverified):', data.lead_id);
                }
                return newSession;

            } catch (e) {
                window.DebugLogger.error('Error parsing session data:', e);
                return this._createNewSession();
            }
        } else {
            return this._createNewSession();
        }
    }

    /**
     * Create a new session for first-time user
     */
    _createNewSession() {
        const now = new Date().toISOString();
        const newSession = {
            session_id: this.generateSessionId(),
            lead_id: null,
            phone: null,
            email: null,
            name: null,
            created_at: now,
            last_activity: now,
            isReturning: false,
            messageCount: 0,
            contactProvidedInSession: false,
            leadVerified: false,
        };

        this._cachedSession = newSession;
        this._saveToStorage(newSession);
        window.DebugLogger.log('New session created:', newSession.session_id);
        return newSession;
    }

    /**
     * Mark lead as verified by the backend.
     * Called after initSession() confirms the lead exists in Dataverse.
     */
    markLeadVerified() {
        if (this._cachedSession) {
            this._cachedSession.leadVerified = true;
            this._saveToStorage(this._cachedSession);
            window.DebugLogger.log('Lead marked as verified:', this._cachedSession.lead_id);
        }
    }

    /**
     * Clear lead_id from session and localStorage.
     * Called when backend reports the lead no longer exists in Dataverse.
     * This prevents the ghost lead_id from being re-sent on the next page load.
     */
    clearLeadId() {
        if (this._cachedSession) {
            window.DebugLogger.log('Clearing stale lead_id:', this._cachedSession.lead_id);
            this._cachedSession.lead_id = null;
            this._cachedSession.leadVerified = false;
            this._cachedSession.isReturning = false;
            this._saveToStorage(this._cachedSession);
        }
    }

    /**
     * Increment user message count
     */
    incrementMessageCount() {
        if (!this._cachedSession) {
            this.getOrCreateSession();
        }

        if (!this._cachedSession.messageCount) {
            this._cachedSession.messageCount = 0;
        }

        this._cachedSession.messageCount++;
        this._saveToStorage(this._cachedSession);

        return this._cachedSession.messageCount;
    }

    /**
     * Get current message count
     */
    getMessageCount() {
        const session = this.getOrCreateSession();
        return session.messageCount || 0;
    }

    /**
     * Reset message count (call this when lead is captured)
     */
    resetMessageCount() {
        if (this._cachedSession) {
            this._cachedSession.messageCount = 0;
            this._saveToStorage(this._cachedSession);
        }
    }

    /**
     * Mark that contact details were provided in this session
     */
    markContactProvided() {
        if (this._cachedSession) {
            this._cachedSession.contactProvidedInSession = true;
            this._saveToStorage(this._cachedSession);
            window.DebugLogger.log('Contact provided flag set for current session');
        }
    }

    /**
     * Internal: Save session to localStorage without triggering cache invalidation
     */
    _saveToStorage(sessionData) {
        localStorage.setItem(this.storageKey, JSON.stringify(sessionData));
    }

    /**
     * Save/update session data to localStorage and update cache
     */
    saveSession(sessionData) {
        sessionData.last_activity = new Date().toISOString();
        this._cachedSession = sessionData;
        this._saveToStorage(sessionData);
    }

    /**
     * Update session with lead information
     * Called when agent captures user's contact info
     */
    updateLeadInfo(leadId, phone, email, name) {
        if (!this._cachedSession) {
            this.getOrCreateSession();
        }

        this._cachedSession.lead_id = leadId;
        this._cachedSession.leadVerified = true; // freshly created — definitely valid
        this._cachedSession.phone = phone || this._cachedSession.phone;
        this._cachedSession.email = email || this._cachedSession.email;
        this._cachedSession.name = name || this._cachedSession.name;

        this.resetMessageCount();
        this.saveSession(this._cachedSession);
        window.DebugLogger.log('Lead info updated:', { leadId, phone, email, name });
    }

    /**
     * Update activity timestamp (lightweight - no session regeneration)
     */
    updateActivity() {
        if (this._cachedSession) {
            this._cachedSession.last_activity = new Date().toISOString();
            this._saveToStorage(this._cachedSession);
        }
    }

    /**
     * Reset in-memory session cache
     */
    resetSession() {
        this._cachedSession = null;
    }

    /**
     * Clear session data (logout/reset)
     */
    clearSession() {
        this._cachedSession = null;
        localStorage.removeItem(this.storageKey);
        window.DebugLogger.log('Session cleared');
    }

    /**
     * Get current session ID
     */
    getSessionId() {
        const session = this.getOrCreateSession();
        return session.session_id;
    }

    /**
     * Get current lead ID (null if not registered)
     */
    getLeadId() {
        const session = this.getOrCreateSession();
        return session.lead_id;
    }

    /**
     * Check if user is a returning user
     */
    isReturningUser() {
        const session = this.getOrCreateSession();
        return session.isReturning && session.lead_id !== null;
    }
}

// Export for use in other modules
window.GoEdSessionManager = SessionManager;
// ============ src/api-client.js ============
/**
 * APIClient - Handles all communication with the FastAPI backend
 * Supports streaming responses via NDJSON
 */

class APIClient {
    constructor(config) {
        this.baseUrl = config.apiUrl;
        this.trialId = config.trialId || null;
    }

    /**
     * Send a chat message and handle streaming response
     */
    async sendMessage(query, sessionId, callbacks, externalSignal = null) {
        const { onToken, onToolStart, onToolEnd, onToolResult, onComplete, onError } = callbacks;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        if (externalSignal) {
            externalSignal.addEventListener('abort', () => controller.abort());
        }

        try {
            const response = await fetch(`${this.baseUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query, 
                    session_id: sessionId,
                    ...(this.trialId && { trial_user_id: this.trialId })
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    window.DebugLogger.log('Stream complete');
                    if (onComplete) onComplete();
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.trim() === '') continue;

                    try {
                        const data = JSON.parse(line);
                        window.DebugLogger.log('Received chunk:', data);

                        if (data.type === 'token') {
                            if (onToken) onToken(data.content, data.node);
                        } else if (data.type === 'tool_start') {
                            window.DebugLogger.log('Tool started:', data.tool_name);
                            if (onToolStart) onToolStart(data.tool_name, data.tool_id);
                        } else if (data.type === 'tool_end') {
                            window.DebugLogger.log('Tool completed:', data.tool_name);
                            if (onToolEnd) onToolEnd(data.tool_name, data.tool_id);
                        } else if (data.type === 'tool_result') {
                            if (onToolResult) onToolResult(data.tool_name, data.content);
                        } else if (data.type === 'error') {
                            window.DebugLogger.error('Backend error:', data.error);
                            if (onError) onError(new Error(data.error));
                        } else if (data.type === 'done' || data.done) {
                            window.DebugLogger.log('Received done signal');
                            if (onComplete) onComplete();
                        } else {
                            window.DebugLogger.warn('Unknown chunk type:', data.type, data);
                        }

                    } catch (e) {
                        window.DebugLogger.error('Error parsing JSON line:', { line, error: e });
                    }
                }
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                window.DebugLogger.error('Request timed out after 60 seconds');
                if (onError) onError(new Error('Request timed out'));
            } else {
                window.DebugLogger.error('Error sending message:', error);
                if (onError) onError(error);
            }
        }
    }

    /**
     * Check if a session is still active
     */
    async checkSessionStatus(sessionId) {
        try {
            const response = await fetch(`${this.baseUrl}/session/${sessionId}/status`);
            return await response.json();
        } catch (error) {
            window.DebugLogger.error('Status check failed:', error);
            return { expired: false, exists: false };
        }
    }

    /**
     * Initialize session with lead_id for returning users.
     *
     * The backend should validate whether the lead_id actually exists in Dataverse
     * and return: { lead_valid: true/false, lead_id: "..." }
     *
     * If lead_valid === false, we clear the stale lead_id from localStorage
     * so it doesn't get sent again on future page loads.
     *
     * @param {string} sessionId - New session ID
     * @param {string|null} leadId - Existing lead ID from localStorage (may be stale)
     * @param {SessionManager} sessionManager - Passed in so we can clear stale lead if needed
     */
    async initSession(sessionId, leadId, sessionManager = null) {
        try {
            const bodyPayload = { session_id: sessionId, lead_id: leadId };
            
            if (this.trialId) {
                bodyPayload.trial_user_id = this.trialId;
            }

            const response = await fetch(`${this.baseUrl}/session/init`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyPayload)
            });

            const data = await response.json();
            window.DebugLogger.log('Session initialized:', data);

            // ── Handle lead validation response from backend ──────────────────
            if (leadId && sessionManager) {
                if (data.lead_valid === false) {
                    // Backend confirmed this lead doesn't exist in Dataverse anymore
                    // Clear it from localStorage so it's never sent again
                    window.DebugLogger.warn(
                        'Lead not found in Dataverse, clearing from localStorage:',
                        leadId
                    );
                    sessionManager.clearLeadId();

                } else if (data.lead_valid === true) {
                    // Backend confirmed lead is valid
                    sessionManager.markLeadVerified();
                    window.DebugLogger.log('Lead verified by backend:', leadId);

                } else {
                    // Backend didn't return lead_valid (older backend version)
                    // Don't clear — assume valid to avoid breaking existing installs
                    window.DebugLogger.log(
                        'Backend did not return lead_valid — assuming lead is valid:', leadId
                    );
                }
            }

            return data;

        } catch (error) {
            window.DebugLogger.error('Error initializing session:', error);
            // Non-critical — don't block the chat
            return null;
        }
    }
}

// Export for use in other modules
window.GoEdAPIClient = APIClient;
// ============ src/ui-manager.js ============
/**
 * MainUIManager - Go Ed AI Edition (Homepage Bot)
 * Professional UI with Robot and Student Icons
 * UPDATED: Fixed DOM query collisions and added unique namespace
 */

class MainUIManager {

    constructor(config) {
        this.config = config;
        this.widgetContainer = null;
        this.messagesContainer = null;
        this.inputField = null;
        this.sendButton = null;
        this.toggleButton = null;
        this.isOpen = false;
        this.currentAIMessageElement = null;

        // Typewriter & Markdown State
        this.typewriterQueue = [];
        this.typewriterTimer = null;
        this.isNetworkStreamDone = false;
        this.currentStreamedText = '';  // Buffer for raw text
        this.typingStartTime = 0;
        this.minTypingMs = 1500;
        this.isTypingVisible = false;
        this.onTypewriterComplete = null;

        // Launcher Bubble State
        this.launcherBubble = null;
        this.currentMessageIndex = 0;
        this.bubbleTimer = null;
    }

    init() {
        this.widgetContainer = this._createWidgetHTML();
        document.body.appendChild(this.widgetContainer);

        // FIX: Strictly query inside THIS widget container to prevent cross-bot collisions
        this.messagesContainer = this.widgetContainer.querySelector('.chatbot-messages');
        this.inputField = this.widgetContainer.querySelector('.chatbot-input');
        this.sendButton = this.widgetContainer.querySelector('.chatbot-send-btn');
        this.toggleButton = this.widgetContainer.querySelector('.chatbot-toggle-btn'); // Changed from document.querySelector
        this.themeToggleBtn = this.widgetContainer.querySelector('.chatbot-theme-toggle');

        if (this.themeToggleBtn) {
            this.themeToggleBtn.addEventListener('click', () => this.toggleTheme());
        }

        this._applyConfig();
        this._setupInputValidation();
        this._initLauncherBubble();
        window.DebugLogger.log('Main UI initialized');
    }

    _setupInputValidation() {
        if (!this.inputField) return;
        
        // Auto-resize logic
        const resizeInput = () => {
            this.inputField.style.height = 'auto';
            const newHeight = Math.min(this.inputField.scrollHeight, 120);
            this.inputField.style.height = newHeight + 'px';
            
            // Add scroll if max height reached
            if (this.inputField.scrollHeight > 120) {
                this.inputField.style.overflowY = 'auto';
            } else {
                this.inputField.style.overflowY = 'hidden';
            }
        };

        this.inputField.addEventListener('input', () => {
            if (this.inputField.value.length > 1000) {
                this.inputField.value = this.inputField.value.substring(0, 1000);
            }
            resizeInput();
        });

        // Also resize on window resize
        window.addEventListener('resize', resizeInput);
        
        // Initial resize
        resizeInput();
    }

    clearMessages() {
        if (this.messagesContainer) {
            this.messagesContainer.innerHTML = '';
        }
    }

    showExpiryMessage(isArchived = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-system-message';

        if (isArchived) {
            messageDiv.innerHTML = `
                <div class="chatbot-message-avatar">
                    🤖
                </div>
                <div class="chatbot-message-bubble chatbot-expiry-archived">
                    <div class="chatbot-message-content">
                        <strong>💾 Session Archived</strong>

                        Your previous conversation has been saved. A new session has been started. Feel free to continue chatting!
                    </div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="chatbot-message-avatar">
                    🤖
                </div>
                <div class="chatbot-message-bubble chatbot-expiry-inactive">
                    <div class="chatbot-message-content">
                        <strong>⏰ Session Expired</strong>

                        Your chat session ended due to inactivity. A new session has been started. Feel free to continue chatting!
                    </div>
                </div>
            `;
        }

        this.messagesContainer.appendChild(messageDiv);
        this._scrollToBottom();

        if (!this.isOpen) {
            this.open();
        }
    }

    showError(message) {
        if (!this.messagesContainer) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'chatbot-message chatbot-message-ai';
        errorDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-message-bubble chatbot-error-bubble">
                <div class="chatbot-message-content chatbot-error-text">
                    ${this._escapeHtml(message)}
                </div>
            </div>
        `;

        this.messagesContainer.appendChild(errorDiv);
        this._scrollToBottom();
    }

    _createWidgetHTML() {
        const container = document.createElement('div');
        container.id = 'main-chatbot-widget-container'; // UNIQUE ID for the homepage bot
        container.className = 'chatbot-widget-container';
        container.innerHTML = `
            <div class="chatbot-launcher-bubble" style="display: none;">
                <span class="bubble-icon">💬</span>
                <span class="bubble-text"></span>
            </div>

            <button class="chatbot-toggle-btn" aria-label="Toggle chat">
                <svg class="chatbot-icon-open" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16ZM7 9H9V11H7V9ZM11 9H13V11H11V9ZM15 9H17V11H15V9Z"/>
                </svg>
                <svg class="chatbot-icon-close" viewBox="0 0 24 24" fill="currentColor" style="display:none;">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
                </svg>
            </button>

            <div class="chatbot-widget" style="display: none;">
                <div class="chatbot-header">
                    <div class="chatbot-header-content">
                        <div class="chatbot-avatar">
                            🤖
                        </div>
                        <div class="chatbot-header-text">
                            <div class="chatbot-title">Go Ed AI Assistant</div>
                            <div class="chatbot-status">
                                <span class="chatbot-status-dot"></span>
                                Online
                            </div>
                        </div>
                    </div>
                    <div class="chatbot-header-actions">
                        <button class="chatbot-header-btn chatbot-theme-toggle" aria-label="Toggle dark mode">
                            <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: none;">
                                <circle cx="12" cy="12" r="5"></circle>
                                <line x1="12" y1="1" x2="12" y2="3"></line>
                                <line x1="12" y1="21" x2="12" y2="23"></line>
                                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                                <line x1="1" y1="12" x2="3" y2="12"></line>
                                <line x1="21" y1="12" x2="23" y2="12"></line>
                                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                            </svg>
                            <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                            </svg>
                        </button>
                        <button class="chatbot-header-btn chatbot-close-btn" aria-label="Close chat">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="chatbot-messages"></div>

                <div class="chatbot-input-area">
                    <textarea
                        class="chatbot-input"
                        placeholder="${this.config.placeholder}"
                        aria-label="Type your message"
                        maxlength="1000"
                        rows="1"
                    ></textarea>
                    <button class="chatbot-send-btn" aria-label="Send message">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>

                <div class="chatbot-footer">
                    <span class="chatbot-powered-by">Powered by Go Ed AI</span>
                </div>
            </div>
        `;
        return container;
    }

    _applyConfig() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');

        // CHECK FOR MOBILE VIEW (768px threshold)
        // If on mobile, we skip applying fixed width/height/offsets 
        // and let the CSS media queries take over fully.
        const isMobile = window.innerWidth <= 768;

        if (!isMobile) {
            // Apply position and offsets only for desktop
            const defaultMargin = 30;
            const xOffset = parseInt(this.config.x) || 0;
            const yOffset = parseInt(this.config.y) || 0;

            if (this.config.position === 'bottom-left') {
                this.widgetContainer.style.left = `${defaultMargin + xOffset}px`;
                this.widgetContainer.style.right = 'auto';
            } else {
                this.widgetContainer.style.right = `${defaultMargin + xOffset}px`;
                this.widgetContainer.style.left = 'auto';
            }

            // Apply vertical offset
            this.widgetContainer.style.bottom = `${defaultMargin + yOffset}px`;
            
            // Apply fixed dimensions
            widget.style.width = this.config.width || '400px';
            widget.style.height = this.config.height || '640px';
        } else {
            // Clear any potential inline styles on mobile to ensure CSS wins
            this.widgetContainer.style.left = '';
            this.widgetContainer.style.right = '';
            this.widgetContainer.style.bottom = '';
            widget.style.width = '';
            widget.style.height = '';
        }

        const root = document.documentElement;
        root.style.setProperty('--cb-color-primary', this.config.primaryColor);

        this._initTheme();
    }

    addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-user';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar" style="background: linear-gradient(135deg, #6366F1, #8B5CF6);">
                🎓
            </div>
            <div class="chatbot-message-content">${this._escapeHtml(text)}</div>
        `;

        this.messagesContainer.appendChild(messageDiv);
        this._scrollToBottom();
    }

    startAIMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-ai';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-message-bubble">
                <div class="chatbot-message-content"></div>
            </div>
        `;

        this.messagesContainer.appendChild(messageDiv);
        this.currentAIMessageElement = messageDiv.querySelector('.chatbot-message-content');
        this._scrollToBottom();

        // Reset typewriter state
        this.typewriterQueue = [];
        this.currentStreamedText = '';
        this.isNetworkStreamDone = false;

        this._startTypewriterLoop();

        return this.currentAIMessageElement;
    }

    appendToAIMessage(token) {
        if (token) {
            const chars = token.split('');
            this.typewriterQueue.push(...chars);
        }
    }

    finishAIMessage(callback = null) {
        this.isNetworkStreamDone = true;
        this.onTypewriterComplete = callback;
    }

    // --- Typewriter Loop ---
    _startTypewriterLoop() {
        if (this.typewriterTimer) clearInterval(this.typewriterTimer);

        this.typewriterTimer = setInterval(() => {
            // Smart Delay: pause typewriter while typing indicator is visible
            if (this.isTypingVisible) return;

            // Adaptive speed: process more chars when queue is large
            const queueLen = this.typewriterQueue.length;
            const charsPerTick = queueLen > 200 ? 5 : queueLen > 100 ? 3 : 1;

            let changed = false;
            for (let i = 0; i < charsPerTick && this.typewriterQueue.length > 0; i++) {
                this.currentStreamedText += this.typewriterQueue.shift();
                changed = true;
            }

            if (changed && this.currentAIMessageElement) {
                this.currentAIMessageElement.innerHTML = this._parseMarkdown(this.currentStreamedText);
                this._scrollToBottom();
            }
            else if (!changed && this.isNetworkStreamDone) {
                clearInterval(this.typewriterTimer);
                this.currentAIMessageElement = null;
                
                // Trigger callback if typewriter is finished
                if (typeof this.onTypewriterComplete === 'function') {
                    this.onTypewriterComplete();
                    this.onTypewriterComplete = null;
                }
            }
        }, 15); // 15ms per tick
    }

    // --- Markdown Parser (powered by marked.js) ---
    _parseMarkdown(text) {
        if (!text) return '';
        return marked.parse(text, { breaks: true, gfm: true });
    }

    showTypingIndicator() {
        this.isTypingVisible = true;
        this.typingStartTime = Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatbot-typing-indicator';
        typingDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        typingDiv.id = 'main-chatbot-typing'; // UNIQUE ID
        this.messagesContainer.appendChild(typingDiv);
        this._scrollToBottom();
    }

    hideTypingIndicator() {
        const elapsed = Date.now() - this.typingStartTime;
        const remaining = this.minTypingMs - elapsed;

        if (remaining > 0) {
            setTimeout(() => this._forceHideIndicator(), remaining);
        } else {
            this._forceHideIndicator();
        }
    }

    _forceHideIndicator() {
        const typingDiv = document.getElementById('main-chatbot-typing');
        if (typingDiv) {
            typingDiv.remove();
        }
        this.isTypingVisible = false;
    }

    showGreeting() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-greeting';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-message-bubble">
                <div class="chatbot-message-content">${this._escapeHtml(this.config.greeting)}</div>
            </div>
        `;

        this.messagesContainer.appendChild(messageDiv);
    }

    clearInput() {
        this.inputField.value = '';
        this.inputField.style.height = 'auto';
        this.inputField.style.overflowY = 'hidden';
    }

    getInputValue() {
        const val = this.inputField.value.trim();
        return val.length > 1000 ? val.substring(0, 1000) : val;
    }

    focusInput() {
        this.inputField.focus();
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
        const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

        widget.style.display = 'flex';
        this.widgetContainer.classList.add('is-open'); // Added for responsive styling
        iconOpen.style.display = 'none';
        iconClose.style.display = 'block';
        this.isOpen = true;

        this.focusInput();

        // Hide launcher bubble when widget is open
        this._hideLauncherBubble();
    }

    close() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
        const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

        widget.style.display = 'none';
        this.widgetContainer.classList.remove('is-open'); // Added for responsive styling
        iconOpen.style.display = 'block';
        iconClose.style.display = 'none';
        this.isOpen = false;

        // Show launcher bubble when widget is closed
        this._showLauncherBubble();
    }

    _scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    disableInput() {
        this.inputField.disabled = true;
        this.sendButton.disabled = true;
    }

    enableInput() {
        this.inputField.disabled = false;
        this.sendButton.disabled = false;
    }

    _initTheme() {
        const savedTheme = localStorage.getItem('main-chatbot-theme');
        const widget = this.widgetContainer.querySelector('.chatbot-widget');

        if (savedTheme === 'dark' || (!savedTheme && this.config.theme === 'dark')) {
            this._setTheme('dark');
        } else {
            this._setTheme('light');
        }
    }

    toggleTheme() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const isDark = widget.classList.contains('chatbot-dark-theme');
        this._setTheme(isDark ? 'light' : 'dark');
    }

    _setTheme(theme) {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const sunIcon = this.widgetContainer.querySelector('.icon-sun');
        const moonIcon = this.widgetContainer.querySelector('.icon-moon');

        if (theme === 'dark') {
            widget.classList.add('chatbot-dark-theme');
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            localStorage.setItem('main-chatbot-theme', 'dark');
        } else {
            widget.classList.remove('chatbot-dark-theme');
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            localStorage.setItem('main-chatbot-theme', 'light');
        }
    }

    // --- Launcher Bubble Methods ---

    _initLauncherBubble() {
        this.launcherBubble = this.widgetContainer.querySelector('.chatbot-launcher-bubble');
        if (!this.launcherBubble || !this.config.launcherMessages || this.config.launcherMessages.length === 0) return;

        // Show the first message
        this._showLauncherBubble();

        // Start cycling
        this._startBubbleCycle();
    }

    _showLauncherBubble() {
        if (!this.launcherBubble || this.isOpen) return;

        const messages = this.config.launcherMessages;
        if (!messages || messages.length === 0) return;

        const textSpan = this.launcherBubble.querySelector('.bubble-text');
        textSpan.textContent = messages[this.currentMessageIndex];

        this.launcherBubble.style.display = 'flex';
        this.launcherBubble.classList.remove('hiding');
        this.launcherBubble.classList.add('showing');
    }

    _hideLauncherBubble() {
        if (!this.launcherBubble) return;
        this.launcherBubble.classList.add('hiding');
        setTimeout(() => {
            if (this.launcherBubble.classList.contains('hiding')) {
                this.launcherBubble.style.display = 'none';
            }
        }, 300);
    }

    _startBubbleCycle() {
        if (this.bubbleTimer) clearInterval(this.bubbleTimer);
        
        const interval = this.config.launcherInterval || 5000;
        const messages = this.config.launcherMessages;

        if (!messages || messages.length <= 1) return;

        this.bubbleTimer = setInterval(() => {
            if (this.isOpen) return;

            // Transition out
            this.launcherBubble.classList.add('hiding');

            setTimeout(() => {
                // Change message
                this.currentMessageIndex = (this.currentMessageIndex + 1) % messages.length;
                const textSpan = this.launcherBubble.querySelector('.bubble-text');
                textSpan.textContent = messages[this.currentMessageIndex];

                // Transition in
                this.launcherBubble.classList.remove('hiding');
                this.launcherBubble.classList.add('showing');
            }, 300);
        }, interval);
    }
}

// EXPORT AS MainUIManager
window.MainUIManager = MainUIManager;

// old
// /**
//  * UIManager - Go Ed AI Edition
//  * Professional UI with Robot and Student Icons
//  */

// class UIManager {

//     constructor(config) {
//         this.config = config;
//         this.widgetContainer = null;
//         this.messagesContainer = null;
//         this.inputField = null;
//         this.sendButton = null;
//         this.toggleButton = null;
//         this.isOpen = false;
//         this.currentAIMessageElement = null;

//         // Typewriter & Markdown State
//         this.typewriterQueue = [];
//         this.typewriterTimer = null;
//         this.isNetworkStreamDone = false;
//         this.currentStreamedText = '';  // Buffer for raw text
//         this.typingStartTime = 0;
//         this.minTypingMs = 1500;
//         this.isTypingVisible = false;
//     }

//     init() {
//         this.widgetContainer = this._createWidgetHTML();
//         document.body.appendChild(this.widgetContainer);

//         this.messagesContainer = this.widgetContainer.querySelector('.chatbot-messages');
//         this.inputField = this.widgetContainer.querySelector('.chatbot-input');
//         this.sendButton = this.widgetContainer.querySelector('.chatbot-send-btn');
//         this.toggleButton = document.querySelector('.chatbot-toggle-btn');
//         this.themeToggleBtn = this.widgetContainer.querySelector('.chatbot-theme-toggle');

//         if (this.themeToggleBtn) {
//             this.themeToggleBtn.addEventListener('click', () => this.toggleTheme());
//         }

//         this._applyConfig();
//         window.DebugLogger.log('UI initialized');
//     }

//     clearMessages() {
//         if (this.messagesContainer) {
//             this.messagesContainer.innerHTML = '';
//         }
//     }

//     showExpiryMessage(isArchived = false) {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-system-message';

//         if (isArchived) {
//             messageDiv.innerHTML = `
//                 <div class="chatbot-message-avatar">
//                     🤖
//                 </div>
//                 <div class="chatbot-message-bubble chatbot-expiry-archived">
//                     <div class="chatbot-message-content">
//                         <strong>💾 Session Archived</strong><br>
//                         Your previous conversation has been saved. A new session has been started. Feel free to continue chatting!
//                     </div>
//                 </div>
//             `;
//         } else {
//             messageDiv.innerHTML = `
//                 <div class="chatbot-message-avatar">
//                     🤖
//                 </div>
//                 <div class="chatbot-message-bubble chatbot-expiry-inactive">
//                     <div class="chatbot-message-content">
//                         <strong>⏰ Session Expired</strong><br>
//                         Your chat session ended due to inactivity. A new session has been started. Feel free to continue chatting!
//                     </div>
//                 </div>
//             `;
//         }

//         this.messagesContainer.appendChild(messageDiv);
//         this._scrollToBottom();

//         if (!this.isOpen) {
//             this.open();
//         }
//     }

//     showError(message) {
//         if (!this.messagesContainer) return;

//         const errorDiv = document.createElement('div');
//         errorDiv.className = 'chatbot-message chatbot-message-ai';
//         errorDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-message-bubble chatbot-error-bubble">
//                 <div class="chatbot-message-content chatbot-error-text">
//                     ${this._escapeHtml(message)}
//                 </div>
//             </div>
//         `;

//         this.messagesContainer.appendChild(errorDiv);
//         this._scrollToBottom();
//     }

//     _createWidgetHTML() {
//         const container = document.createElement('div');
//         container.className = 'chatbot-widget-container';
//         container.innerHTML = `
//             <!-- Toggle Button with Chat Icon -->
//             <button class="chatbot-toggle-btn" aria-label="Toggle chat">
//                 <svg class="chatbot-icon-open" viewBox="0 0 24 24" fill="currentColor">
//                     <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16ZM7 9H9V11H7V9ZM11 9H13V11H11V9ZM15 9H17V11H15V9Z"/>
//                 </svg>
//                 <svg class="chatbot-icon-close" viewBox="0 0 24 24" fill="currentColor" style="display:none;">
//                     <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
//                 </svg>
//             </button>

//             <!-- Main Widget -->
//             <div class="chatbot-widget" style="display: none;">
//                 <!-- Header -->
//                 <div class="chatbot-header">
//                     <div class="chatbot-header-content">
//                         <div class="chatbot-avatar">
//                             🤖
//                         </div>
//                         <div class="chatbot-header-text">
//                             <div class="chatbot-title">Go Ed AI Assistant</div>
//                             <div class="chatbot-status">
//                                 <span class="chatbot-status-dot"></span>
//                                 Online
//                             </div>
//                         </div>
//                     </div>
//                     <div class="chatbot-header-actions">
//                         <button class="chatbot-header-btn chatbot-theme-toggle" aria-label="Toggle dark mode">
//                             <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: none;">
//                                 <circle cx="12" cy="12" r="5"></circle>
//                                 <line x1="12" y1="1" x2="12" y2="3"></line>
//                                 <line x1="12" y1="21" x2="12" y2="23"></line>
//                                 <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
//                                 <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
//                                 <line x1="1" y1="12" x2="3" y2="12"></line>
//                                 <line x1="21" y1="12" x2="23" y2="12"></line>
//                                 <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
//                                 <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
//                             </svg>
//                             <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
//                                 <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
//                             </svg>
//                         </button>
//                         <button class="chatbot-header-btn chatbot-close-btn" aria-label="Close chat">
//                             <svg viewBox="0 0 24 24" fill="currentColor">
//                                 <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
//                             </svg>
//                         </button>
//                     </div>
//                 </div>

//                 <!-- Messages Area -->
//                 <div class="chatbot-messages"></div>

//                 <!-- Input Area -->
//                 <div class="chatbot-input-area">
//                     <input
//                         type="text"
//                         class="chatbot-input"
//                         placeholder="${this.config.placeholder}"
//                         aria-label="Type your message"
//                     />
//                     <button class="chatbot-send-btn" aria-label="Send message">
//                         <svg viewBox="0 0 24 24" fill="currentColor">
//                             <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
//                         </svg>
//                     </button>
//                 </div>

//                 <!-- Footer -->
//                 <div class="chatbot-footer">
//                     <span class="chatbot-powered-by">Powered by Go Ed AI</span>
//                 </div>
//             </div>
//         `;
//         return container;
//     }

//     _applyConfig() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');

//         if (this.config.position === 'bottom-left') {
//             this.widgetContainer.style.left = '24px';
//             this.widgetContainer.style.right = 'auto';
//         }

//         const root = document.documentElement;
//         root.style.setProperty('--cb-color-primary', this.config.primaryColor);

//         this._initTheme();

//         widget.style.width = this.config.width || '400px';
//         widget.style.height = this.config.height || '640px';
//     }

//     addUserMessage(text) {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-user';
//         messageDiv.innerHTML = `
//             <div class="chatbot-message-avatar" style="background: linear-gradient(135deg, #6366F1, #8B5CF6);">
//                 🎓
//             </div>
//             <div class="chatbot-message-content">${this._escapeHtml(text)}</div>
//         `;

//         this.messagesContainer.appendChild(messageDiv);
//         this._scrollToBottom();
//     }

//     startAIMessage() {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-ai';
//         messageDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-message-bubble">
//                 <div class="chatbot-message-content"></div>
//             </div>
//         `;

//         this.messagesContainer.appendChild(messageDiv);
//         this.currentAIMessageElement = messageDiv.querySelector('.chatbot-message-content');
//         this._scrollToBottom();

//         // Reset typewriter state
//         this.typewriterQueue = [];
//         this.currentStreamedText = '';
//         this.isNetworkStreamDone = false;

//         this._startTypewriterLoop();

//         return this.currentAIMessageElement;
//     }

//     appendToAIMessage(token) {
//         if (token) {
//             const chars = token.split('');
//             this.typewriterQueue.push(...chars);
//         }
//     }

//     finishAIMessage() {
//         this.isNetworkStreamDone = true;
//     }

//     // --- Typewriter Loop ---
//     _startTypewriterLoop() {
//         if (this.typewriterTimer) clearInterval(this.typewriterTimer);

//         this.typewriterTimer = setInterval(() => {
//             // Smart Delay: pause typewriter while typing indicator is visible
//             if (this.isTypingVisible) return;

//             // Adaptive speed: process more chars when queue is large
//             const queueLen = this.typewriterQueue.length;
//             const charsPerTick = queueLen > 200 ? 5 : queueLen > 100 ? 3 : 1;

//             let changed = false;
//             for (let i = 0; i < charsPerTick && this.typewriterQueue.length > 0; i++) {
//                 this.currentStreamedText += this.typewriterQueue.shift();
//                 changed = true;
//             }

//             if (changed && this.currentAIMessageElement) {
//                 this.currentAIMessageElement.innerHTML = this._parseMarkdown(this.currentStreamedText);
//                 this._scrollToBottom();
//             }
//             else if (!changed && this.isNetworkStreamDone) {
//                 clearInterval(this.typewriterTimer);
//                 this.currentAIMessageElement = null;
//             }
//         }, 15); // 15ms per tick
//     }

//     // --- Markdown Parser (powered by marked.js) ---
//     _parseMarkdown(text) {
//         if (!text) return '';
//         return marked.parse(text, { breaks: true, gfm: true });
//     }

//     showTypingIndicator() {
//         this.isTypingVisible = true;
//         this.typingStartTime = Date.now();
//         const typingDiv = document.createElement('div');
//         typingDiv.className = 'chatbot-typing-indicator';
//         typingDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-typing-dots">
//                 <span></span>
//                 <span></span>
//                 <span></span>
//             </div>
//         `;
//         typingDiv.id = 'chatbot-typing';
//         this.messagesContainer.appendChild(typingDiv);
//         this._scrollToBottom();
//     }

//     hideTypingIndicator() {
//         const elapsed = Date.now() - this.typingStartTime;
//         const remaining = this.minTypingMs - elapsed;

//         if (remaining > 0) {
//             setTimeout(() => this._forceHideIndicator(), remaining);
//         } else {
//             this._forceHideIndicator();
//         }
//     }

//     _forceHideIndicator() {
//         const typingDiv = document.getElementById('chatbot-typing');
//         if (typingDiv) {
//             typingDiv.remove();
//         }
//         this.isTypingVisible = false;
//     }

//     showGreeting() {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-greeting';
//         messageDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-message-bubble">
//                 <div class="chatbot-message-content">${this._escapeHtml(this.config.greeting)}</div>
//             </div>
//         `;

//         this.messagesContainer.appendChild(messageDiv);
//     }

//     clearInput() {
//         this.inputField.value = '';
//     }

//     getInputValue() {
//         return this.inputField.value.trim();
//     }

//     focusInput() {
//         this.inputField.focus();
//     }

//     toggle() {
//         if (this.isOpen) {
//             this.close();
//         } else {
//             this.open();
//         }
//     }

//     open() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
//         const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

//         widget.style.display = 'flex';
//         iconOpen.style.display = 'none';
//         iconClose.style.display = 'block';
//         this.isOpen = true;

//         this.focusInput();
//     }

//     close() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
//         const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

//         widget.style.display = 'none';
//         iconOpen.style.display = 'block';
//         iconClose.style.display = 'none';
//         this.isOpen = false;
//     }

//     _scrollToBottom() {
//         this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
//     }

//     _escapeHtml(text) {
//         const div = document.createElement('div');
//         div.textContent = text;
//         return div.innerHTML;
//     }

//     disableInput() {
//         this.inputField.disabled = true;
//         this.sendButton.disabled = true;
//     }

//     enableInput() {
//         this.inputField.disabled = false;
//         this.sendButton.disabled = false;
//     }

//     _initTheme() {
//         const savedTheme = localStorage.getItem('chatbot-theme');
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');

//         if (savedTheme === 'dark' || (!savedTheme && this.config.theme === 'dark')) {
//             this._setTheme('dark');
//         } else {
//             this._setTheme('light');
//         }
//     }

//     toggleTheme() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const isDark = widget.classList.contains('chatbot-dark-theme');
//         this._setTheme(isDark ? 'light' : 'dark');
//     }

//     _setTheme(theme) {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const sunIcon = this.widgetContainer.querySelector('.icon-sun');
//         const moonIcon = this.widgetContainer.querySelector('.icon-moon');

//         if (theme === 'dark') {
//             widget.classList.add('chatbot-dark-theme');
//             sunIcon.style.display = 'block';
//             moonIcon.style.display = 'none';
//             localStorage.setItem('chatbot-theme', 'dark');
//         } else {
//             widget.classList.remove('chatbot-dark-theme');
//             sunIcon.style.display = 'none';
//             moonIcon.style.display = 'block';
//             localStorage.setItem('chatbot-theme', 'light');
//         }
//     }
// }

// window.UIManager = UIManager;
// ============ src/chatbot-widget.js ============
/**
* ChatbotWidget - Main controller that orchestrates all components
* This is the entry point and public API
* UPDATED: Now properly handles tool_start and tool_end events and uses isolated MainUIManager
*/
(function () {
    'use strict';



    class ChatbotWidget {
        constructor() {
            this.config = null;
            this.sessionManager = null;
            this.apiClient = null;
            this.uiManager = null;
            this.initialized = false;
            this.pollingInterval = null;
            this._currentAbortController = null;
        }



        /**
         * Initialize the chatbot widget
         * @param {Object} userConfig - User configuration
         */
        init(userConfig = {}) {
            if (this.initialized) {
                window.DebugLogger.warn('Chatbot already initialized');
                return;
            }



            // Validate required trialId
            if (!userConfig.trialId && !window.ChatbotConfig.trialId) {
                window.DebugLogger.error('CRITICAL ERROR: Initialization aborted. A valid trialId must be provided in the initialization configuration. Unauthorized widget usage is blocked.');
                return;
            }

            // Merge user config with defaults
            this.config = { ...window.ChatbotConfig, ...userConfig };
            this.config.expiryDays = this.config.sessionExpiryDays;



            // Initialize components
            this.sessionManager = new window.GoEdSessionManager(this.config);
            this.apiClient = new window.GoEdAPIClient(this.config);

            // ==========================================
            // FIX: Using MainUIManager instead of UIManager
            // ==========================================
            this.uiManager = new window.MainUIManager(this.config);



            // Initialize UI
            this.uiManager.init();



            // Set up event listeners
            this._setupEventListeners();



            // Initialize session
            this._initializeSession();



            // Start inactivity polling
            this._startInactivityPolling();



            // Show greeting
            this.uiManager.showGreeting();



            this.initialized = true;
            window.DebugLogger.log('Chatbot widget initialized successfully');
        }



        /**
         * Initialize session (handle returning users and trial mode)
         */
        async _initializeSession() {
            const session = this.sessionManager.getOrCreateSession();

            const isReturning = session.isReturning && session.lead_id;
            const hasTrialId = !!this.config.trialId;

            // If returning user or trial ID is provided, initialize backend session
            if (isReturning || hasTrialId) {
                window.DebugLogger.log('Initializing backend session (returning user or trial mode)');
                await this.apiClient.initSession(session.session_id, session.lead_id || null);

                if (isReturning) {
                    // Reset message count for returning users with lead_id
                    this.sessionManager.resetMessageCount();
                }
            }
        }



        /**
         * Start polling backend for session expiry
         */
        _startInactivityPolling() {
            if (this.pollingInterval) clearInterval(this.pollingInterval);



            this.pollingInterval = setInterval(async () => {
                const session = this.sessionManager.getOrCreateSession();
                const sessionId = session.session_id;
                if (!sessionId) return;



                // Check backend status
                const status = await this.apiClient.checkSessionStatus(sessionId);
                window.DebugLogger.log(`Polling session ${sessionId.substring(0, 16)}... status:`, status);



                // If session expired on backend
                if (status && status.expired === true) {
                    window.DebugLogger.warn('Session expired due to inactivity (detected by polling)');



                    // Stop polling temporarily to prevent multiple triggers
                    clearInterval(this.pollingInterval);



                    // Show expiry message
                    this.uiManager.showExpiryMessage();



                    // Clear local session data
                    const oldLeadId = this.sessionManager.getLeadId();
                    this.sessionManager.resetSession();



                    // Create new session
                    const newSession = this.sessionManager.getOrCreateSession();
                    window.DebugLogger.log(`New session created: ${newSession.session_id}`);



                    // Re-initialize on backend if returning user OR trial mode
                    const hasTrialId = !!this.config.trialId;
                    if (oldLeadId || hasTrialId) {
                        await this.apiClient.initSession(newSession.session_id, oldLeadId || null);
                        window.DebugLogger.log(`Initialized new session on backend (lead: ${oldLeadId}, trial: ${hasTrialId})`);
                    }



                    // Restart polling with new session
                    this._startInactivityPolling();
                }
            }, 60000); // Check every 60 seconds
        }



        /**
         * Setup all event listeners
         */
        _setupEventListeners() {
            // Toggle button
            this.uiManager.toggleButton.addEventListener('click', () => {
                this.uiManager.toggle();
            });



            // Close button
            const closeBtn = this.uiManager.widgetContainer.querySelector('.chatbot-close-btn');
            closeBtn.addEventListener('click', () => {
                this.uiManager.close();
            });



            // Send button
            this.uiManager.sendButton.addEventListener('click', () => {
                this._handleSendMessage();
            });



            // Input field - Enter key
            this.uiManager.inputField.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this._handleSendMessage();
                }
            });



            // Input field - Update activity on typing
            this.uiManager.inputField.addEventListener('input', () => {
                this.sessionManager.updateActivity();
            });
        }



        /**
         * Handle sending a message
         */
        async _handleSendMessage() {
            const message = this.uiManager.getInputValue();



            if (!message) {
                return;
            }



            const session = this.sessionManager.getOrCreateSession();
            const sessionId = session.session_id;



            // Only check session status if:
            // 1. This is a returning user (has lead_id), OR
            // 2. This session has already sent messages before
            const shouldCheckStatus = session.isReturning || this.sessionManager.getMessageCount() > 0;



            if (shouldCheckStatus) {
                window.DebugLogger.log(`Checking session ${sessionId} status...`);
                const status = await this.apiClient.checkSessionStatus(sessionId);
                window.DebugLogger.log('Session status:', status);



                if (status && status.expired === true) {
                    window.DebugLogger.warn('Session expired - creating new session before sending message');



                    // Show expiry message
                    this.uiManager.showExpiryMessage();



                    // Create new session
                    const oldLeadId = this.sessionManager.getLeadId();
                    this.sessionManager.resetSession();
                    const newSession = this.sessionManager.getOrCreateSession();



                    // Re-link lead_id or initialize trial
                    const hasTrialId = !!this.config.trialId;
                    if (oldLeadId || hasTrialId) {
                        await this.apiClient.initSession(newSession.session_id, oldLeadId || null);
                    }



                    // Now continue with the message using new session
                    const newSessionId = newSession.session_id;
                    this._sendMessageToBackend(message, newSessionId);
                    return;
                }
            } else {
                window.DebugLogger.log('Skipping status check for brand new session');
            }



            // Session is valid (or new), send normally
            this._sendMessageToBackend(message, sessionId);
        }



        /**
         * Actually send the message to backend
         */
        async _sendMessageToBackend(message, sessionId) {
            // Abort any in-flight request
            if (this._currentAbortController) {
                this._currentAbortController.abort();
            }
            this._currentAbortController = new AbortController();
            const signal = this._currentAbortController.signal;



            // Increment message count
            this.sessionManager.incrementMessageCount();



            // Add user message to UI
            this.uiManager.addUserMessage(message);
            this.uiManager.clearInput();
            this.uiManager.disableInput();



            // Show typing indicator
            this.uiManager.showTypingIndicator();



            // Update activity
            this.sessionManager.updateActivity();



            await this.apiClient.sendMessage(message, sessionId, {
                onToken: (content, node) => {
                    // Remove typing indicator on first token
                    this.uiManager.hideTypingIndicator();



                    // Start AI message if not started
                    if (!this.uiManager.currentAIMessageElement) {
                        this.uiManager.startAIMessage();
                    }



                    // Append token
                    this.uiManager.appendToAIMessage(content);
                },



                // Handle tool_start events
                onToolStart: (toolName, toolId) => {
                    window.DebugLogger.log(`Tool started: ${toolName}`);
                    // Removed hideTypingIndicator to keep dots visible during tool calls
                },



                // Handle tool_end events
                onToolEnd: (toolName, toolId) => {
                    window.DebugLogger.log(`Tool completed: ${toolName}`);
                },



                onToolResult: (toolName, content) => {
                    window.DebugLogger.log(`Tool ${toolName} executed:`, content);



                    // If check_lead or create_lead was called, user has shared contact info
                    if (toolName === 'check_lead' || toolName === 'create_lead') {
                        // Mark that contact was provided (regardless of found/not_found)
                        this.sessionManager.markContactProvided();



                        // Handle lead capture for successful cases
                        this._handleLeadCapture(content);
                    }
                },



                onComplete: () => {
                    window.DebugLogger.log('Message stream complete');
                    this.uiManager.hideTypingIndicator();
                    this.uiManager.finishAIMessage(() => {
                        this.uiManager.enableInput();
                        this.uiManager.focusInput();
                    });
                    this._currentAbortController = null;
                },



                onError: (error) => {
                    window.DebugLogger.error('Error sending message:', error);
                    this.uiManager.hideTypingIndicator();
                    this.uiManager.showError('Failed to send message. Please try again.');
                    this.uiManager.enableInput();
                    this.uiManager.focusInput();
                    this._currentAbortController = null;
                }
            }, signal);
        }



        /**
         * Handle lead capture from tool results
         * @param {string} toolContent - Tool result content (JSON string)
         */
        _handleLeadCapture(toolContent) {
            try {
                let data = toolContent;



                // Parse JSON string
                if (typeof data === 'string') {
                    data = JSON.parse(data);
                }



                // Handle array format: [{type: 'text', text: '...'}]
                if (Array.isArray(data) && data.length > 0) {
                    const item = data[0];
                    if (item.text && typeof item.text === 'string') {
                        data = JSON.parse(item.text);
                    } else if (typeof item === 'object') {
                        data = item;
                    }
                }



                // Handle single object with text field: {type: 'text', text: '...'}
                if (data.type === 'text' && data.text) {
                    data = JSON.parse(data.text);
                }



                // Check if lead was successfully captured
                if (data.status === 'success' && data.lead_id) {
                    window.DebugLogger.log('Lead captured:', data.lead_id);



                    // Update session with lead info (this also resets message count)
                    this.sessionManager.updateLeadInfo(
                        data.lead_id,
                        data.phone || null,
                        data.email || null,
                        data.name || null
                    );
                } else if (data.status === 'not_found') {
                    window.DebugLogger.log('Contact details provided but lead not found in system');
                    // Contact was provided, just not found - this is fine
                    // contactProvidedInSession is already marked in onToolResult
                }
            } catch (e) {
                // Only log unexpected errors (not "not_found" cases)
                if (!String(toolContent).includes('"status":"not_found"')) {
                    window.DebugLogger.error('Error parsing lead capture data:', { error: e.message, content: toolContent });
                }
            }
        }



        /**
         * Public API: Send message programmatically
         */
        sendMessage(message) {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }



            this.uiManager.inputField.value = message;
            this._handleSendMessage();
        }



        /**
         * Public API: Open widget
         */
        open() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }
            this.uiManager.open();
        }



        /**
         * Public API: Close widget
         */
        close() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }
            this.uiManager.close();
        }



        /**
         * Public API: Clear session
         */
        clearSession() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }
            this.sessionManager.clearSession();
            window.DebugLogger.log('Session cleared. Refresh page to start new session.');
        }



        /**
         * Public API: Get session info (for debugging)
         */
        getSessionInfo() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return null;
            }



            return {
                session_id: this.sessionManager.getSessionId(),
                lead_id: this.sessionManager.getLeadId(),
                is_returning: this.sessionManager.isReturningUser(),
                message_count: this.sessionManager.getMessageCount()
            };
        }
    }



    // ==========================================
    // CHANGES APPLIED HERE
    // ==========================================

    // Export for global access
    window.ChatbotWidget = ChatbotWidget;

    // Create global instance as mainChatbotWidget
    window.mainChatbotWidget = new ChatbotWidget();



    // Auto-initialize on DOMContentLoaded if config exists
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            if (window.mainChatbotAutoInit) {
                window.mainChatbotWidget.init(window.mainChatbotAutoInit);
            }
        });
    } else {
        // DOM already loaded (script loaded with defer/async or after DOMContentLoaded)
        if (window.mainChatbotAutoInit) {
            window.mainChatbotWidget.init(window.mainChatbotAutoInit);
        }
    }



})();

//old
// /**
//  * ChatbotWidget - Main controller that orchestrates all components
//  * This is the entry point and public API
//  * UPDATED: Now properly handles tool_start and tool_end events
//  */

// (function () {
//     'use strict';

//     class ChatbotWidget {
//         constructor() {
//             this.config = null;
//             this.sessionManager = null;
//             this.apiClient = null;
//             this.uiManager = null;
//             this.initialized = false;
//             this.pollingInterval = null;
//             this._currentAbortController = null;
//         }

//         /**
//          * Initialize the chatbot widget
//          * @param {Object} userConfig - User configuration
//          */
//         init(userConfig = {}) {
//             if (this.initialized) {
//                 window.DebugLogger.warn('Chatbot already initialized');
//                 return;
//             }

//             // Merge user config with defaults
//             this.config = { ...window.ChatbotConfig, ...userConfig };
//             this.config.expiryDays = this.config.sessionExpiryDays;

//             // Initialize components
//             this.sessionManager = new window.SessionManager(this.config);
//             this.apiClient = new window.APIClient(this.config);
//             this.uiManager = new window.UIManager(this.config);

//             // Initialize UI
//             this.uiManager.init();

//             // Set up event listeners
//             this._setupEventListeners();

//             // Initialize session
//             this._initializeSession();

//             // Start inactivity polling
//             this._startInactivityPolling();

//             // Show greeting
//             this.uiManager.showGreeting();

//             this.initialized = true;
//             window.DebugLogger.log('Chatbot widget initialized successfully');
//         }

//         /**
//          * Initialize session (handle returning users)
//          */
//         async _initializeSession() {
//             const session = this.sessionManager.getOrCreateSession();

//             // If returning user with lead_id, initialize backend session
//             if (session.isReturning && session.lead_id) {
//                 window.DebugLogger.log('Returning user detected, initializing session with lead_id');
//                 await this.apiClient.initSession(session.session_id, session.lead_id);
//                 // Reset message count for returning users with lead_id
//                 this.sessionManager.resetMessageCount();
//             }
//         }

//         /**
//          * Start polling backend for session expiry
//          */
//         _startInactivityPolling() {
//             if (this.pollingInterval) clearInterval(this.pollingInterval);

//             this.pollingInterval = setInterval(async () => {
//                 const session = this.sessionManager.getOrCreateSession();
//                 const sessionId = session.session_id;
//                 if (!sessionId) return;

//                 // Check backend status
//                 const status = await this.apiClient.checkSessionStatus(sessionId);
//                 window.DebugLogger.log(`Polling session ${sessionId.substring(0, 16)}... status:`, status);

//                 // If session expired on backend
//                 if (status && status.expired === true) {
//                     window.DebugLogger.warn('Session expired due to inactivity (detected by polling)');

//                     // Stop polling temporarily to prevent multiple triggers
//                     clearInterval(this.pollingInterval);

//                     // Clear old messages from UI
//                     this.uiManager.clearMessages();

//                     // Show expiry message
//                     this.uiManager.showExpiryMessage();

//                     // Clear local session data
//                     const oldLeadId = this.sessionManager.getLeadId();
//                     this.sessionManager.resetSession();

//                     // Create new session
//                     const newSession = this.sessionManager.getOrCreateSession();
//                     window.DebugLogger.log(`New session created: ${newSession.session_id}`);

//                     // Re-initialize on backend with old lead_id if exists
//                     if (oldLeadId) {
//                         await this.apiClient.initSession(newSession.session_id, oldLeadId);
//                         window.DebugLogger.log(`Linked old lead_id ${oldLeadId} to new session`);
//                     }

//                     // Restart polling with new session
//                     this._startInactivityPolling();
//                 }
//             }, 60000); // Check every 60 seconds
//         }

//         /**
//          * Setup all event listeners
//          */
//         _setupEventListeners() {
//             // Toggle button
//             this.uiManager.toggleButton.addEventListener('click', () => {
//                 this.uiManager.toggle();
//             });

//             // Close button
//             const closeBtn = this.uiManager.widgetContainer.querySelector('.chatbot-close-btn');
//             closeBtn.addEventListener('click', () => {
//                 this.uiManager.close();
//             });

//             // Send button
//             this.uiManager.sendButton.addEventListener('click', () => {
//                 this._handleSendMessage();
//             });

//             // Input field - Enter key
//             this.uiManager.inputField.addEventListener('keypress', (e) => {
//                 if (e.key === 'Enter' && !e.shiftKey) {
//                     e.preventDefault();
//                     this._handleSendMessage();
//                 }
//             });

//             // Input field - Update activity on typing
//             this.uiManager.inputField.addEventListener('input', () => {
//                 this.sessionManager.updateActivity();
//             });
//         }

//         /**
//          * Handle sending a message
//          */
//         async _handleSendMessage() {
//             const message = this.uiManager.getInputValue();

//             if (!message) {
//                 return;
//             }

//             const session = this.sessionManager.getOrCreateSession();
//             const sessionId = session.session_id;

//             // Only check session status if:
//             // 1. This is a returning user (has lead_id), OR
//             // 2. This session has already sent messages before
//             const shouldCheckStatus = session.isReturning || this.sessionManager.getMessageCount() > 0;

//             if (shouldCheckStatus) {
//                 window.DebugLogger.log(`Checking session ${sessionId} status...`);
//                 const status = await this.apiClient.checkSessionStatus(sessionId);
//                 window.DebugLogger.log('Session status:', status);

//                 if (status && status.expired === true) {
//                     window.DebugLogger.warn('Session expired - creating new session before sending message');

//                     // Clear old messages
//                     this.uiManager.clearMessages();

//                     // Show expiry message
//                     this.uiManager.showExpiryMessage();

//                     // Create new session
//                     const oldLeadId = this.sessionManager.getLeadId();
//                     this.sessionManager.resetSession();
//                     const newSession = this.sessionManager.getOrCreateSession();

//                     // Re-link lead_id
//                     if (oldLeadId) {
//                         await this.apiClient.initSession(newSession.session_id, oldLeadId);
//                     }

//                     // Now continue with the message using new session
//                     const newSessionId = newSession.session_id;
//                     this._sendMessageToBackend(message, newSessionId);
//                     return;
//                 }
//             } else {
//                 window.DebugLogger.log('Skipping status check for brand new session');
//             }

//             // Session is valid (or new), send normally
//             this._sendMessageToBackend(message, sessionId);
//         }

//         /**
//          * Actually send the message to backend
//          */
//         async _sendMessageToBackend(message, sessionId) {
//             // Abort any in-flight request
//             if (this._currentAbortController) {
//                 this._currentAbortController.abort();
//             }
//             this._currentAbortController = new AbortController();
//             const signal = this._currentAbortController.signal;

//             // Increment message count
//             this.sessionManager.incrementMessageCount();

//             // Add user message to UI
//             this.uiManager.addUserMessage(message);
//             this.uiManager.clearInput();
//             this.uiManager.disableInput();

//             // Show typing indicator
//             this.uiManager.showTypingIndicator();

//             // Update activity
//             this.sessionManager.updateActivity();

//             await this.apiClient.sendMessage(message, sessionId, {
//                 onToken: (content, node) => {
//                     // Remove typing indicator on first token
//                     this.uiManager.hideTypingIndicator();

//                     // Start AI message if not started
//                     if (!this.uiManager.currentAIMessageElement) {
//                         this.uiManager.startAIMessage();
//                     }

//                     // Append token
//                     this.uiManager.appendToAIMessage(content);
//                 },

//                 // Handle tool_start events
//                 onToolStart: (toolName, toolId) => {
//                     window.DebugLogger.log(`Tool started: ${toolName}`);
//                     this.uiManager.hideTypingIndicator();
//                 },

//                 // Handle tool_end events
//                 onToolEnd: (toolName, toolId) => {
//                     window.DebugLogger.log(`Tool completed: ${toolName}`);
//                 },

//                 onToolResult: (toolName, content) => {
//                     window.DebugLogger.log(`Tool ${toolName} executed:`, content);

//                     // If check_lead or create_lead was called, user has shared contact info
//                     if (toolName === 'check_lead' || toolName === 'create_lead') {
//                         // Mark that contact was provided (regardless of found/not_found)
//                         this.sessionManager.markContactProvided();

//                         // Handle lead capture for successful cases
//                         this._handleLeadCapture(content);
//                     }
//                 },

//                 onComplete: () => {
//                     window.DebugLogger.log('Message stream complete');
//                     this.uiManager.hideTypingIndicator();
//                     this.uiManager.finishAIMessage();
//                     this.uiManager.enableInput();
//                     this.uiManager.focusInput();
//                     this._currentAbortController = null;
//                 },

//                 onError: (error) => {
//                     window.DebugLogger.error('Error sending message:', error);
//                     this.uiManager.hideTypingIndicator();
//                     this.uiManager.showError('Failed to send message. Please try again.');
//                     this.uiManager.enableInput();
//                     this.uiManager.focusInput();
//                     this._currentAbortController = null;
//                 }
//             }, signal);
//         }

//         /**
//          * Handle lead capture from tool results
//          * @param {string} toolContent - Tool result content (JSON string)
//          */
//         _handleLeadCapture(toolContent) {
//             try {
//                 let data = toolContent;

//                 // Parse JSON string
//                 if (typeof data === 'string') {
//                     data = JSON.parse(data);
//                 }

//                 // Handle array format: [{type: 'text', text: '...'}]
//                 if (Array.isArray(data) && data.length > 0) {
//                     const item = data[0];
//                     if (item.text && typeof item.text === 'string') {
//                         data = JSON.parse(item.text);
//                     } else if (typeof item === 'object') {
//                         data = item;
//                     }
//                 }

//                 // Handle single object with text field: {type: 'text', text: '...'}
//                 if (data.type === 'text' && data.text) {
//                     data = JSON.parse(data.text);
//                 }

//                 // Check if lead was successfully captured
//                 if (data.status === 'success' && data.lead_id) {
//                     window.DebugLogger.log('Lead captured:', data.lead_id);

//                     // Update session with lead info (this also resets message count)
//                     this.sessionManager.updateLeadInfo(
//                         data.lead_id,
//                         data.phone || null,
//                         data.email || null,
//                         data.name || null
//                     );
//                 } else if (data.status === 'not_found') {
//                     window.DebugLogger.log('Contact details provided but lead not found in system');
//                     // Contact was provided, just not found - this is fine
//                     // contactProvidedInSession is already marked in onToolResult
//                 }
//             } catch (e) {
//                 // Only log unexpected errors (not "not_found" cases)
//                 if (!String(toolContent).includes('"status":"not_found"')) {
//                     window.DebugLogger.error('Error parsing lead capture data:', { error: e.message, content: toolContent });
//                 }
//             }
//         }

//         /**
//          * Public API: Send message programmatically
//          */
//         sendMessage(message) {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }

//             this.uiManager.inputField.value = message;
//             this._handleSendMessage();
//         }

//         /**
//          * Public API: Open widget
//          */
//         open() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }
//             this.uiManager.open();
//         }

//         /**
//          * Public API: Close widget
//          */
//         close() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }
//             this.uiManager.close();
//         }

//         /**
//          * Public API: Clear session
//          */
//         clearSession() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }
//             this.sessionManager.clearSession();
//             window.DebugLogger.log('Session cleared. Refresh page to start new session.');
//         }

//         /**
//          * Public API: Get session info (for debugging)
//          */
//         getSessionInfo() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return null;
//             }

//             return {
//                 session_id: this.sessionManager.getSessionId(),
//                 lead_id: this.sessionManager.getLeadId(),
//                 is_returning: this.sessionManager.isReturningUser(),
//                 message_count: this.sessionManager.getMessageCount()
//             };
//         }
//     }

//     // Create global instance
//     window.ChatbotWidget = new ChatbotWidget();

//     // Auto-initialize on DOMContentLoaded if config exists
//     if (document.readyState === 'loading') {
//         document.addEventListener('DOMContentLoaded', () => {
//             if (window.ChatbotAutoInit) {
//                 window.ChatbotWidget.init(window.ChatbotAutoInit);
//             }
//         });
//     } else {
//         // DOM already loaded (script loaded with defer/async or after DOMContentLoaded)
//         if (window.ChatbotAutoInit) {
//             window.ChatbotWidget.init(window.ChatbotAutoInit);
//         }
//     }

// })();

