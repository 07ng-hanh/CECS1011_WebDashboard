async function createNewUser() {
    let username = document.getElementById("edit-username-text").value
    let password = document.getElementById("edit-user-password").value
    e = await axios.post("/admin/new-user", {
        "username": username,
        "password": password,
        "isadmin": false
    },  {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            }
        })

    if (e.status === 200) {
        createUserModalToggle(false)
        await getAndShowUsers(user_page)
        return null
    }

    if (e.status === 422) {
        alert("Username has already been used.")
        return null
    }

    if (e.status !== 200 && e.status !== 422) {
        alert("Server error.")
        return null
    }



}

function createUserModalToggle(visible) {
    if (visible) {
        document.getElementById("editor-user-modal").style.display = "flex"
    } else {
        let username = document.getElementById("edit-username-text")
        let password = document.getElementById("edit-user-password")

        username.value = ""
        password.value = ""

        document.getElementById("editor-user-modal").style.display = "none"

    }
}

function _getCookie(name) {
  const nameEQ = name + "=";
  const ca = document.cookie.split(';'); // Split the document.cookie string into an array of individual cookie strings

  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') { // Remove leading whitespace
      c = c.substring(1);
    }
    if (c.indexOf(nameEQ) === 0) { // Check if this cookie string starts with the desired name
      return c.substring(nameEQ.length, c.length); // Return the value part of the cookie
    }
  }
  return null; // Return null if the cookie is not found
}

function showUsersInGrid(users, start_index) {
    let tbl =  document.querySelector("#user-table tbody")
    tbl.innerHTML = ""


    for (let i = 0; i < users.length; i++) {
        let row = document.createElement("tr")
        let username_cell = document.createElement("td")
        let id_cell = document.createElement("td")
        let actions = document.createElement("td")

        actions.className = "action-cell"

        let actions_remove = document.createElement("button")
        actions_remove.addEventListener("click", async ()=>{
            await removeUserByUserName(users[i].username)
        })

        actions_remove.innerText = "Remove"
        actions_remove.className = "sm danger"

        let actions_reset_pwd = document.createElement("button")
        actions_reset_pwd.addEventListener("click", async() => {
            await promptReplaceUserPassword(users[i].username)
        })

        actions_reset_pwd.innerText = "Change Password"
        actions_reset_pwd.className = "sm"

        let is_admin_cell = document.createElement("td")

        username_cell.innerText = users[i].username
        is_admin_cell.innerText = users[i].isadmin ? "Yes" : "No"
        id_cell.innerText = i + start_index

        actions.appendChild(actions_reset_pwd)

        if (_getCookie("username") !== users[i].username) {
            actions.appendChild(actions_remove)
        }

        row.appendChild(id_cell)
        row.appendChild(username_cell)
        row.appendChild(is_admin_cell)
        row.appendChild(actions)

        tbl.appendChild(row)
    }



}

async function removeUserByUserName(username) {
    if (confirm(`Delete user ${username}?`)) {
        a = await axios.delete("/admin/delete-user",  {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            },
            params: {
                username: username
            }
        })

        if (a.status !== 200) {
            alert(`Exited with error ${a.status}`)
        } else {
            await getAndShowUsers(user_page)
        }


    }
}

async function promptReplaceUserPassword(username) {

    if (username === _getCookie("username")) {
        window.location.href = '#reset-password'
        document.getElementById("password").focus()
        return
    }

    let newpwd = prompt(`Set new password for user ${username}. This will invalidate all sessions for this user.`)
    if (newpwd != null) {

        let d = await axios.post("/admin/change-user-password", {
            username: username,
            password: newpwd
        },  {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            }
        })

        if (d.status !== 200) {
            alert(`Operation failed with code ${d.status}`)
        }

    }


}

let user_page = 1
let user_page_lim = 50
let user_page_query = ""
async function getAndShowUsers(page) {

    if (page < 1) {
        page = 1
    }

    user_page = page
    let d = await axios.get("/admin/list-users",  {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            },
            params: {
                page: user_page,
                limit: user_page_lim,
                query: user_page_query
            }
        })

    if (d.status === 200) {
        console.log(d.data)
        showUsersInGrid(d.data, (user_page - 1) * user_page_lim + 1)
        document.getElementById("page-user").innerText = user_page
    } else {
        alert("Cannot fetch user list from server.")
    }
}

async function queryUsers() {
    user_page_query = document.getElementById("search-username-00x").value
    user_page = 1
    getAndShowUsers(user_page)
}



let user_search_debounce_timer = undefined

document.addEventListener("DOMContentLoaded", async() => {
    user_page = 1
    await getAndShowUsers(user_page)

    document.getElementById("search-username-00x").addEventListener("input", () => {
        if (user_search_debounce_timer !== undefined) {
            clearTimeout(user_search_debounce_timer)

        }
        user_search_debounce_timer = setTimeout(() => {
            queryUsers()
        }, 300)
    })

})

