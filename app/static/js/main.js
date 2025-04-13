// Refresh news id to get latest news

document.addEventListener('DOMContentLoaded', function() {
    const newsContainer = document.getElementById('news-container');
    
    async function refreshNews() {
        try {
            console.log('Attempting to refresh news...');
            // Add timestamp to prevent caching
            const response = await fetch(`/latest-news?t=${Date.now()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const html = await response.text();
            //console.log('Received HTML:', html.substring(0, 100) + '...'); // Log first 100 chars
            newsContainer.innerHTML = html;
            // console.log('News refreshed at:', new Date().toLocaleTimeString());
        } catch (error) {
            console.error('Error refreshing news:', error);
            // Optional: show error to user
            newsContainer.innerHTML = `
                <div class="bg-red-900 text-white p-4 rounded">
                    Error loading news. Please try again later.
                </div>
            `;
        }
    }
    // Initial load
    refreshNews();
    
    // Refresh every second (1000ms)
    setInterval(refreshNews, 100000);
});



// Function to hide sidebar 
document.addEventListener("DOMContentLoaded", function() {
    const sidebar = document.getElementById('sidebar');
    const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');

    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('hidden');
        
        // Update the icon based on sidebar state
        const icon = toggleSidebarBtn.querySelector('i');
        if (sidebar.classList.contains('hidden')) {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
            // Move the button to the left edge when sidebar is hidden
            toggleSidebarBtn.parentElement.classList.add('fixed', 'left-0', 'top-4');
            toggleSidebarBtn.parentElement.classList.remove('flex', 'items-center', 'justify-between');
        } else {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
            // Return the button to its original position
            toggleSidebarBtn.parentElement.classList.remove('fixed', 'left-0', 'top-4');
            toggleSidebarBtn.parentElement.classList.add('flex', 'items-center', 'justify-between');
        }
    });
});