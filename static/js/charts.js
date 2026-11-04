/* ============================================================
   轻量图表库（Canvas 自绘，无第三方依赖）
   支持：环形图 doughnut / 柱状图 bar / 折线图 line
   数据来源：window.DASH_DATA（由首页模板注入）
   ============================================================ */
(function () {
  "use strict";

  var COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
                "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16"];
  var FONT = '"Microsoft YaHei", "Segoe UI", sans-serif';

  // 按设备像素比初始化画布，保证清晰度
  function setup(canvas) {
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || canvas.parentElement.clientWidth || 300;
    var h = canvas.clientHeight || 260;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx: ctx, w: w, h: h };
  }

  function drawEmpty(ctx, w, h) {
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "14px " + FONT;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("暂无数据", w / 2, h / 2);
  }

  /* ---------------- 环形图（性别分布） ---------------- */
  function drawDoughnut(canvas, data) {
    var s = setup(canvas), ctx = s.ctx, w = s.w, h = s.h;
    var total = data.reduce(function (a, b) { return a + (b.value || 0); }, 0);
    if (!total) { drawEmpty(ctx, w, h); return; }

    var cx = w * 0.36, cy = h / 2;
    var r = Math.min(w * 0.22, h * 0.34), inner = r * 0.55;
    var start = -Math.PI / 2;

    data.forEach(function (d, i) {
      var angle = (d.value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.strokeStyle = COLORS[i % COLORS.length];
      ctx.lineWidth = r - inner;
      ctx.lineCap = "butt";
      ctx.stroke();
      start += angle;
    });

    // 中心总计
    ctx.fillStyle = "#1e293b";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "bold 22px " + FONT;
    ctx.fillText(String(total), cx, cy - 10);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "12px " + FONT;
    ctx.fillText("总人数", cx, cy + 14);

    // 右侧图例
    var lx = w * 0.62;
    var ly = h / 2 - (data.length - 1) * 14;
    ctx.textBaseline = "middle";
    data.forEach(function (d, i) {
      var y = ly + i * 30;
      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.fillRect(lx, y - 6, 12, 12);
      ctx.fillStyle = "#475569";
      ctx.textAlign = "left";
      ctx.font = "13px " + FONT;
      var pct = Math.round((d.value / total) * 100);
      ctx.fillText(d.label + "  " + d.value + " 人（" + pct + "%）", lx + 20, y);
    });
  }

  /* ---------------- 柱状图（班级人数） ---------------- */
  function drawBar(canvas, labels, values) {
    var s = setup(canvas), ctx = s.ctx, w = s.w, h = s.h;
    if (!values.length) { drawEmpty(ctx, w, h); return; }

    var padL = 42, padR = 12, padT = 22, padB = 34;
    var cw = w - padL - padR, ch = h - padT - padB;
    var max = Math.max.apply(null, values);
    var steps = 4;
    var bw = Math.min(40, (cw / labels.length) * 0.55);

    // 横向网格与 Y 轴刻度
    ctx.font = "11px " + FONT;
    for (var i = 0; i <= steps; i++) {
      var gy = padT + ch - (ch * i / steps);
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padL, gy);
      ctx.lineTo(w - padR, gy);
      ctx.stroke();
      ctx.fillStyle = "#94a3b8";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(String(Math.round(max * i / steps)), padL - 8, gy);
    }

    // 柱体 + 数值 + X 轴标签
    ctx.textAlign = "center";
    values.forEach(function (v, i) {
      var x = padL + (cw * (i + 0.5)) / labels.length;
      var bh = (ch * v) / max;
      var y = padT + ch - bh;

      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x - bw / 2, y, bw, Math.max(bh, 1), [4, 4, 0, 0]);
        ctx.fill();
      } else {
        ctx.fillRect(x - bw / 2, y, bw, Math.max(bh, 1));
      }

      ctx.fillStyle = "#334155";
      ctx.font = "11px " + FONT;
      ctx.fillText(String(v), x, y - 7);

      ctx.fillStyle = "#64748b";
      ctx.fillText(String(labels[i]).slice(0, 10), x, padT + ch + 18);
    });
  }

  /* ---------------- 折线图（入学年份趋势） ---------------- */
  function drawLine(canvas, labels, values) {
    var s = setup(canvas), ctx = s.ctx, w = s.w, h = s.h;
    if (!values.length) { drawEmpty(ctx, w, h); return; }

    var padL = 42, padR = 16, padT = 22, padB = 34;
    var cw = w - padL - padR, ch = h - padT - padB;
    var max = Math.max.apply(null, values);
    var steps = 4;

    ctx.font = "11px " + FONT;
    for (var i = 0; i <= steps; i++) {
      var gy = padT + ch - (ch * i / steps);
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padL, gy);
      ctx.lineTo(w - padR, gy);
      ctx.stroke();
      ctx.fillStyle = "#94a3b8";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(String(Math.round(max * i / steps)), padL - 8, gy);
    }

    function pt(i) {
      var x = padL + (cw * (i + 0.5)) / labels.length;
      var y = padT + ch - (ch * values[i]) / max;
      return { x: x, y: y };
    }

    // 面积填充
    var first = pt(0), last = pt(values.length - 1);
    var grad = ctx.createLinearGradient(0, padT, 0, padT + ch);
    grad.addColorStop(0, "rgba(37, 99, 235, 0.22)");
    grad.addColorStop(1, "rgba(37, 99, 235, 0.02)");
    ctx.beginPath();
    ctx.moveTo(first.x, padT + ch);
    ctx.lineTo(first.x, first.y);
    values.forEach(function (_, i) { ctx.lineTo(pt(i).x, pt(i).y); });
    ctx.lineTo(last.x, padT + ch);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // 折线
    ctx.beginPath();
    values.forEach(function (_, i) {
      var p = pt(i);
      if (i === 0) { ctx.moveTo(p.x, p.y); } else { ctx.lineTo(p.x, p.y); }
    });
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.stroke();

    // 数据点与标签
    ctx.textAlign = "center";
    values.forEach(function (v, i) {
      var p = pt(i);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = "#2563eb";
      ctx.lineWidth = 2.5;
      ctx.stroke();

      ctx.fillStyle = "#334155";
      ctx.font = "11px " + FONT;
      ctx.fillText(String(v), p.x, p.y - 12);
      ctx.fillStyle = "#64748b";
      ctx.fillText(String(labels[i]), p.x, padT + ch + 18);
    });
  }

  /* ---------------- 渲染入口 ---------------- */
  function renderAll() {
    var data = window.DASH_DATA;
    if (!data) { return; }

    var genderCanvas = document.getElementById("genderChart");
    if (genderCanvas) { drawDoughnut(genderCanvas, data.gender_data || []); }

    var classCanvas = document.getElementById("classChart");
    if (classCanvas) {
      drawBar(classCanvas, (data.class_data && data.class_data.labels) || [],
              (data.class_data && data.class_data.values) || []);
    }

    var yearCanvas = document.getElementById("yearChart");
    if (yearCanvas) {
      drawLine(yearCanvas, (data.year_data && data.year_data.labels) || [],
               (data.year_data && data.year_data.values) || []);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderAll();
    var timer = null;
    window.addEventListener("resize", function () {
      clearTimeout(timer);
      timer = setTimeout(renderAll, 200);
    });
  });
})();