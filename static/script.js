const qInput = document.getElementById('q');
const searchBtn = document.getElementById('search');
const list = document.getElementById('list');
const count = document.getElementById('count');

async function doSearch(){
  const q = qInput.value.trim();
  if(!q) return;
  list.innerHTML = 'جارٍ البحث...';
  count.textContent = '';
  try{
    const res = await fetch(`/search?q=${encodeURIComponent(q)}&limit=200`);
    const data = await res.json();
    list.innerHTML = '';
    count.textContent = `النتائج: ${data.count}`;
    if(data.count === 0){
      list.innerHTML = '<li>لا توجد نتائج</li>';
      return;
    }
    data.results.forEach(item => {
      const li = document.createElement('li');
      const title = document.createElement('strong');
      title.textContent = item['رقم المادة'];
      const p = document.createElement('p');
      p.textContent = item['نص المادة'];
      li.appendChild(title);
      li.appendChild(p);
      list.appendChild(li);
    });
  }catch(e){
    list.innerHTML = '<li>حدث خطأ أثناء البحث</li>';
    console.error(e);
  }
}

searchBtn.addEventListener('click', doSearch);
qInput.addEventListener('keypress', (e)=>{ if(e.key==='Enter') doSearch(); });
