import { searchFilter } from "./filter.js";
import { renderArticle, renderHot } from "./render.js";


let articleSource = [];


document.addEventListener("DOMContentLoaded", async () => {

  console.log("app.js 已加载");


  // =========================
  // 获取分类弹窗元素
  // =========================

  const box = document.getElementById("categoryBox");
  const toggleBtn = document.getElementById("toggleCategoryBox");


  console.log("box:", box);
  console.log("btn:", toggleBtn);


  // =========================
  // 获取文章数据
  // =========================

  const response = await fetch("/api/report");

  articleSource = await response.json();


  console.log("文章数据:", articleSource);



  // 初始渲染

  renderArticle(articleSource);

  renderHot(articleSource);



  // =========================
  // 绑定功能
  // =========================

  bindCategory();

  bindSearch();


});



// =========================
// 搜索
// =========================

function bindSearch(){


  const input =
  document.getElementById("searchInput");


  if(!input){
    return;
  }



  input.addEventListener("input",(e)=>{


    const keyword =
    e.target.value;



    const list =
    searchFilter(
      articleSource,
      keyword
    );



    renderArticle(list);

    renderHot(list);



  });


}