document.addEventListener('DOMContentLoaded', function() {
    // Deadline countdown
    const deadlines = document.querySelectorAll('.deadline');
    deadlines.forEach(el => {
        const dueDate = new Date(el.dataset.due);
        const now = new Date();
        const diff = dueDate - now;
        
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            el.textContent = `Due in ${days} days`;
        } else {
            el.textContent = 'Past due';
            el.style.color = 'red';
        }
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const textareas = this.querySelectorAll('textarea');
            let valid = true;
            
            textareas.forEach(ta => {
                if (ta.value.trim() === '') {
                    ta.style.border = '1px solid red';
                    valid = false;
                }
            });
            
            if (!valid) {
                e.preventDefault();
                alert('Please fill all required fields');
            }
        });
    });
});