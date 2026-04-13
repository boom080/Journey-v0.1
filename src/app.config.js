export default defineAppConfig({
  pages: [
    "pages/home/main",
    "pages/journey/main",
    "pages/profile/main",
    "pages/auth/index",
    "pages/invite/index",
    "pages/food/main",
    "pages/activity/main"
  ],
  window: {
    navigationBarBackgroundColor: "#F4FFF8",
    navigationBarTitleText: "Journey",
    navigationBarTextStyle: "black",
    backgroundColor: "#F4FFF8",
    backgroundTextStyle: "light"
  },
  tabBar: {
    color: "#769888",
    selectedColor: "#1E8B62",
    backgroundColor: "#FFFFFF",
    borderStyle: "black",
    list: [
      {
        pagePath: "pages/home/main",
        text: "首页"
      },
      {
        pagePath: "pages/journey/main",
        text: "里程"
      },
      {
        pagePath: "pages/profile/main",
        text: "我的"
      }
    ]
  }
});
