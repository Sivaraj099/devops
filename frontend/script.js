// Point API to your EC2 instance public IP instead of localhost
const API_BASE = "http://3.110.245.75:5000";  
// OR you can use your EC2 public DNS:
// const API_BASE = "http://ec2-3-110-245-75.ap-south-1.compute.amazonaws.com:5000";

let allEmployees = []; // Cache for filtering

// Handle form submit (Add or Update)
document.getElementById("employeeForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const name = document.getElementById("name").value;
  const role = document.getElementById("role").value;
  const email = document.getElementById("email").value;
  const field = document.getElementById("field").value;
  const organization = document.getElementById("organization").value;
  const empId = document.getElementById("employeeId").value; // hidden input

  const payload = { name, role, email, field, organization };

  try {
    let response;
    if (empId) {
      // UPDATE employee
      response = await fetch(`${API_BASE}/employees/${empId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, role, email }) 
      });
      document.getElementById("result").innerHTML = ""; 
    } else {
      // ADD employee
      response = await fetch(`${API_BASE}/employees`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (response.ok) {
        document.getElementById("result").innerHTML = `
          <h3>✅ Onboarding Initiated for ${name}</h3>
          <h4>Onboarding Checklist:</h4>
          <ul>${data.checklist.map(item => `<li>${item}</li>`).join("")}</ul>
          <h4>AI-Generated Welcome Email Draft:</h4>
          <p>${data.welcome_email}</p>
        `;
      } else {
        throw new Error(data.error || "An unknown error occurred.");
      }
    }
    
    if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || "An unknown error occurred.");
    }

    document.getElementById("employeeId").value = "";
    document.getElementById("submitBtn").innerText = "Add Employee";
    
  } catch (error) {
    alert(`Error: ${error.message}`);
  } finally {
    loadEmployees();
    e.target.reset();
  }
});

// Render the employee list
function renderEmployees(employees) {
  document.getElementById("employeeList").innerHTML = employees
    .map(emp => `
      <li>
        <div class="employee-info">
          <strong>${emp.name}</strong> (${emp.role})<br>
          <small>${emp.email}</small>
        </div>
        <div class="actions">
          <button class="edit-btn" onclick="editEmployee(${emp.id}, '${emp.name}', '${emp.role}', '${emp.email}')">✏️ Edit</button>
          <button class="delete-btn" onclick="deleteEmployee(${emp.id})">🗑️ Delete</button>
        </div>
      </li>
    `)
    .join("");
}

// Load All Employees
async function loadEmployees() {
  try {
    const res = await fetch(`${API_BASE}/employees`);
    allEmployees = await res.json();
    renderEmployees(allEmployees);
    document.getElementById("roleFilter").value = "";
  } catch (error) {
    console.error("Failed to load employees:", error);
  }
}

// Filter Employees by Role
function filterEmployees() {
  const filterValue = document.getElementById("roleFilter").value.toLowerCase();
  if (!filterValue) {
    renderEmployees(allEmployees);
    return;
  }
  const filtered = allEmployees.filter(emp => emp.role.toLowerCase().includes(filterValue));
  renderEmployees(filtered);
}

// Edit Employee
function editEmployee(id, name, role, email) {
  document.getElementById("name").value = name;
  document.getElementById("role").value = role;
  document.getElementById("email").value = email;
  document.getElementById("employeeId").value = id;
  document.getElementById("submitBtn").innerText = "Update Employee";

  document.getElementById("field").value = "";
  document.getElementById("organization").value = "";
  
  window.scrollTo(0, 0);
}

// Delete Employee
async function deleteEmployee(id) {
  if (!confirm("Are you sure you want to delete this employee?")) return;

  try {
    const response = await fetch(`${API_BASE}/employees/${id}`, {
      method: "DELETE"
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    alert(data.message);
  } catch (error) {
    alert(`Error: ${error.message}`);
  } finally {
    loadEmployees();
  }
}

// Initial load
loadEmployees();
