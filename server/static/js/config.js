const serverList = document.getElementById('serverList');
const collapseBtn = document.getElementById('collapseBtn');
const collapseSvg = document.getElementById('collapseSvg');
const serversTitle = document.getElementById('serversTitle');

collapseBtn.addEventListener('click', () => {
    serverList.classList.toggle('w-1/4');
    serverList.classList.toggle('w-42');
    serverList.classList.toggle('collapsed');
    serversTitle.classList.toggle('hidden');
    
    if (serverList.classList.contains('collapsed')) {
        collapseSvg.setAttribute('d', 'M9 5l7 7-7 7');
    } else {
        collapseSvg.setAttribute('d', 'M15 19l-7-7 7-7');
    }
});