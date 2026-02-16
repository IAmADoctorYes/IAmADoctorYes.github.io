let POSTS = [];
let resultsContainer = document.getElementById("posts");

fetch("/assets/search-index.json")
  .then(r => r.json())
  .then(data => {
    POSTS = data;
    renderPosts(POSTS);
  });

function renderPosts(list){
  resultsContainer.innerHTML = "";

  list.forEach(post=>{
    const el = document.createElement("div");
    el.className = "post-preview";
    el.innerHTML = `
      <h3><a href="/blog/${post.slug}">${post.title}</a></h3>
      <p>${post.preview}...</p>
      <small>${post.tags.join(", ")}</small>
    `;
    resultsContainer.appendChild(el);
  });
}

document.getElementById("search").addEventListener("input", e=>{
  const q = e.target.value.toLowerCase();

  const filtered = POSTS.filter(p =>
    p.title.toLowerCase().includes(q) ||
    p.preview.toLowerCase().includes(q) ||
    p.tags.join(" ").toLowerCase().includes(q)
  );

  renderPosts(filtered);
});
