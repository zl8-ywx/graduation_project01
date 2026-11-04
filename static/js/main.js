/* 全局交互逻辑：侧边栏开关、危险操作确认、消息自动消失 */
document.addEventListener("DOMContentLoaded", function () {
  // 移动端侧边栏开关
  var toggle = document.getElementById("menuToggle");
  var sidebar = document.getElementById("sidebar");
  var mask = document.getElementById("mask");
  if (toggle && sidebar && mask) {
    toggle.addEventListener("click", function () {
      sidebar.classList.add("open");
      mask.classList.add("show");
    });
    mask.addEventListener("click", function () {
      sidebar.classList.remove("open");
      mask.classList.remove("show");
    });
  }

  // 带 data-confirm 的表单提交前确认
  document.querySelectorAll("form.js-del").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      var msg = f.getAttribute("data-confirm") || "确定执行该操作吗？";
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // 提示消息 4 秒后自动淡出
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      el.classList.add("fade-out");
      setTimeout(function () { el.remove(); }, 500);
    }, 4000);
  });

  // 右上角用户下拉菜单：修改密码 / 退出登录
  var userBtn = document.getElementById("userMenuBtn");
  var userDrop = document.getElementById("userDropdown");
  if (userBtn && userDrop) {
    userBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      userDrop.classList.toggle("show");
    });
    document.addEventListener("click", function (e) {
      if (!userDrop.contains(e.target) && !userBtn.contains(e.target)) {
        userDrop.classList.remove("show");
      }
    });
  }
});