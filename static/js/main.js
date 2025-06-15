// Main JavaScript for Yoqilg'i Quyish Stansiyalari

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Flash message auto close
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            const closeButton = message.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000); // Auto close after 5 seconds
    });

    // Mobile menu toggler animation
    const menuToggler = document.querySelector('.navbar-toggler');
    if (menuToggler) {
        menuToggler.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    }

    // Favorite button functionality
    const favoriteButtons = document.querySelectorAll('[id^="favorite-btn-"]');
    favoriteButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const stationId = this.getAttribute('data-station-id');
            toggleFavorite(stationId, this);
        });
    });

    // Function to toggle favorite status
    function toggleFavorite(stationId, buttonElement) {
        fetch(`/toggle_favorite/${stationId}`)
            .then(response => response.json())
            .then(data => {
                const icon = buttonElement.querySelector('i');
                if (data.status === 'added') {
                    icon.classList.remove('fa-heart-broken');
                    icon.classList.add('fa-heart');
                    buttonElement.setAttribute('title', 'Sevimlilardan o\'chirish');
                    showToast('Stansiya sevimlilarga qo\'shildi');
                } else {
                    icon.classList.remove('fa-heart');
                    icon.classList.add('fa-heart-broken');
                    buttonElement.setAttribute('title', 'Sevimlilarga qo\'shish');
                    showToast('Stansiya sevimlilardan o\'chirildi');
                }
            })
            .catch(error => {
                console.error('Error toggling favorite:', error);
                showToast('Xatolik yuz berdi. Qaytadan urinib ko\'ring.');
            });
    }

    // Show toast notification
    function showToast(message) {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.setAttribute('id', toastId);
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas fa-info-circle me-2 text-primary"></i>
                <strong class="me-auto">Bildirishnoma</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        const toastElement = new bootstrap.Toast(toast);
        toastElement.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
    }

    // Scroll to top button
    const scrollTopBtn = document.getElementById('scroll-top-btn');
    if (scrollTopBtn) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollTopBtn.style.display = 'block';
            } else {
                scrollTopBtn.style.display = 'none';
            }
        });

        scrollTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // Animate elements on scroll
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    if (animatedElements.length > 0) {
        function checkIfInView() {
            animatedElements.forEach(function(element) {
                const elementTop = element.getBoundingClientRect().top;
                const elementVisible = 150;
                
                if (elementTop < window.innerHeight - elementVisible) {
                    element.classList.add('fade-in');
                }
            });
        }

        // Initial check
        checkIfInView();
        
        // Check on scroll
        window.addEventListener('scroll', checkIfInView);
    }
});

// Geolocation helper
function getUserLocation(callback) {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            // Success callback
            function(position) {
                callback({
                    success: true,
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                });
            },
            // Error callback
            function(error) {
                let errorMessage;
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = "Joylashuvni aniqlash uchun ruxsat berilmadi.";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = "Joylashuv ma'lumotlari mavjud emas.";
                        break;
                    case error.TIMEOUT:
                        errorMessage = "Joylashuvni aniqlash so'rovi vaqti tugadi.";
                        break;
                    case error.UNKNOWN_ERROR:
                        errorMessage = "Noma'lum xatolik yuz berdi.";
                        break;
                }
                callback({
                    success: false,
                    error: errorMessage
                });
            }
        );
    } else {
        callback({
            success: false,
            error: "Brauzeringizda geolokatsiya qo'llab-quvvatlanmaydi."
        });
    }
}