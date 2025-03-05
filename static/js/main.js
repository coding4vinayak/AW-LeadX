// Lead assignment functionality
function assignLead(leadId) {
    document.getElementById('leadId').value = leadId;
    
    // Fetch available clients
    fetch('/api/clients')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch clients');
            }
            return response.json();
        })
        .then(clients => {
            const userSelect = document.getElementById('userId');
            userSelect.innerHTML = '<option value="">Select a client...</option>';
            
            clients.forEach(client => {
                const option = document.createElement('option');
                option.value = client.id;
                option.textContent = `${client.name} (${client.email})`;
                userSelect.appendChild(option);
            });
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('assignLeadModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load clients. Please try again.');
        });
}

// Handle lead assignment form submission
document.getElementById('assignLeadForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const leadId = document.getElementById('leadId').value;
    const userId = document.getElementById('userId').value;
    
    if (!userId) {
        alert('Please select a client');
        return;
    }
    
    fetch(`/api/leads/${leadId}/assign`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to assign lead');
            });
        }
        return response.json();
    })
    .then(data => {
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('assignLeadModal'));
        modal.hide();
        
        // Refresh the page to show updated assignments
        window.location.reload();
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message);
    });
});