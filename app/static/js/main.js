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
                console.log('Received HTML:', html.substring(0, 100) + '...'); // Log first 100 chars
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
        setInterval(refreshNews, 1000);
    });
