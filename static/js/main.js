// Main JavaScript for Online Job Portal

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // AJAX Bookmark Job Toggle
  const saveButtons = document.querySelectorAll('.btn-save-job');
  saveButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const jobId = btn.dataset.jobId;
      if (!jobId) return;

      try {
        const response = await fetch(`/jobs/${jobId}/save`, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
          }
        });

        if (response.redirected) {
          window.location.href = response.url;
          return;
        }

        const data = await response.json();
        const icon = btn.querySelector('i');
        const textSpan = btn.querySelector('.save-text');

        if (data.status === 'saved') {
          if (icon) {
            icon.classList.remove('bi-bookmark');
            icon.classList.add('bi-bookmark-fill', 'text-primary');
          }
          if (textSpan) textSpan.textContent = 'Saved';
          showToast('Job Saved', data.message || 'Job added to bookmarks', 'success');
        } else if (data.status === 'unsaved') {
          if (icon) {
            icon.classList.remove('bi-bookmark-fill', 'text-primary');
            icon.classList.add('bi-bookmark');
          }
          if (textSpan) textSpan.textContent = 'Save Job';
          showToast('Job Removed', data.message || 'Job removed from bookmarks', 'info');

          // If on saved jobs page, remove card smoothly
          const card = btn.closest('.saved-job-item');
          if (card) {
            card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            card.style.opacity = '0';
            card.style.transform = 'scale(0.95)';
            setTimeout(() => card.remove(), 300);
          }
        }
      } catch (err) {
        console.error('Error toggling saved job:', err);
      }
    });
  });

  // Copy Job Link Utility
  const copyBtns = document.querySelectorAll('.btn-copy-link');
  copyBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const url = window.location.href;
      navigator.clipboard.writeText(url).then(() => {
        showToast('Link Copied', 'Job link copied to clipboard!', 'success');
      });
    });
  });
});

// Toast notification helper
function showToast(title, message, type = 'info') {
  let toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1090';
    document.body.appendChild(toastContainer);
  }

  const toastId = 'toast_' + Date.now();
  const bgClass = type === 'success' ? 'bg-success text-white' : type === 'danger' ? 'bg-danger text-white' : 'bg-primary text-white';

  const toastHtml = `
    <div id="${toastId}" class="toast align-items-center ${bgClass} border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          <strong>${title}:</strong> ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);
  const toastElem = document.getElementById(toastId);
  const bsToast = new bootstrap.Toast(toastElem, { delay: 3500 });
  bsToast.show();
  toastElem.addEventListener('hidden.bs.toast', () => toastElem.remove());
}
