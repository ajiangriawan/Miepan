document.addEventListener("DOMContentLoaded", (event) => {
  const stars = document.querySelectorAll(".star");
  const ratingInput = document.getElementById("rating");

  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const rating = star.getAttribute("data-value");
      ratingInput.value = rating;

      stars.forEach((s) => {
        if (s.getAttribute("data-value") <= rating) {
          s.classList.remove("far");
          s.classList.add("fas");
        } else {
          s.classList.remove("fas");
          s.classList.add("far");
        }
      });
    });
  });
});

document.addEventListener("DOMContentLoaded", (event) => {
  const ctx = document.getElementById("salesChart").getContext("2d");
  let salesChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Penjualan",
          data: [],
          backgroundColor: "#eeeeee",
          borderColor: "#d31a20",
          borderWidth: 1,
          fill: true,
        },
      ],
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });

  function fetchData(period) {
    fetch(`/sales_data?period=${period}`)
      .then((response) => response.json())
      .then((data) => {
        const labels = data.map((item) => item.date);
        const salesData = data.map((item) => item.sales);

        salesChart.data.labels = labels;
        salesChart.data.datasets[0].data = salesData;
        salesChart.update();
      });
  }

  window.updateChart = function (period) {
    fetchData(period);
  };

  // Load initial data for weekly view
  fetchData("weekly");
});

function filterCategory(category) {
  let cards = document.querySelectorAll(".menu-card");
  cards.forEach((card) => {
    if (category === "All" || card.getAttribute("data-category") === category) {
      card.style.display = "block";
    } else {
      card.style.display = "none";
    }
  });
}

function filterMenu(category) {
  window.location.href = "/menu?category=" + category;
}

function find_word() {
  let input = document.getElementById("input-word").value.toLowerCase();
  let cards = document.querySelectorAll(".menu-card");
  cards.forEach((card) => {
    let name = card
      .querySelector(".col-md-3.d-flex.justify-content-start")
      .textContent.toLowerCase();
    if (name.includes(input)) {
      card.style.display = "block";
    } else {
      card.style.display = "none";
    }
  });
}

function find_menu() {
  var input = document.getElementById("input-word").value.toLowerCase();
  var cards = document.getElementsByClassName("menu-card");

  for (var i = 0; i < cards.length; i++) {
    var card = cards[i];
    var title = card
      .getElementsByClassName("card-title")[0]
      .innerText.toLowerCase();
    if (title.includes(input)) {
      card.parentElement.style.display = "";
    } else {
      card.parentElement.style.display = "none";
    }
  }
}

function find_menuhome() {
  var input = document.getElementById("input-word").value;
  if (input) {
    window.location.href = `/menu?search=${encodeURIComponent(input)}`;
  }
}

window.onload = function () {
  const params = new URLSearchParams(window.location.search);
  const searchQuery = params.get("search");
  if (searchQuery) {
    document.getElementById("input-word").value = searchQuery;
    find_menu();
  }
};

document.addEventListener("DOMContentLoaded", function () {
  fetch("/cart_count")
    .then((response) => response.json())
    .then((data) => {
      if (data.total_items !== undefined) {
        document.getElementById("total_cart").innerText = data.total_items;
      }
    })
    .catch((error) => console.error("Error fetching cart count:", error));
});

function updateQuantity(itemId, action) {
  fetch(`/update_quantity/${itemId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action: action }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        document.getElementById(`qty-${itemId}`).textContent =
          data.new_quantity;
        const newTotalPrice =
          data.new_quantity *
          parseInt(
            document
              .querySelector(`#checkbox-${itemId}`)
              .closest(".card")
              .querySelector(".item-price").textContent
          );
        document.getElementById(`total-price-${itemId}`).textContent =
          newTotalPrice.toLocaleString("id-ID");
        updateTotals();
      } else {
        alert(data.message);
      }
    });
}

function deleteItemFromCart(itemId) {
  if (confirm("Apakah Anda yakin ingin menghapus item ini dari keranjang?")) {
    fetch(`/delete_item/${itemId}`, {
      method: "DELETE",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Hapus elemen dari tampilan
          document
            .getElementById(`checkbox-${itemId}`)
            .closest(".card")
            .remove();
          updateTotals();
        } else {
          alert(data.message);
        }
      });
  }
}

function updateTotals() {
  const checkboxes = document.querySelectorAll(".item-checkbox");
  let totalItems = 0;
  let totalAmount = 0;

  checkboxes.forEach((checkbox) => {
    if (checkbox.checked) {
      const itemId = checkbox.id.split("-")[1];
      const quantity = parseInt(
        document.getElementById(`qty-${itemId}`).textContent
      );
      const price = parseInt(
        document
          .querySelector(`#checkbox-${itemId}`)
          .closest(".card")
          .querySelector(".item-price").textContent
      );
      totalItems += quantity;
      totalAmount += price * quantity;
    }
  });

  document.getElementById("total-items").textContent = totalItems;
  document.getElementById("total-amount").textContent =
    "Rp. " + totalAmount.toLocaleString("id-ID") + ",-";
}

function toggleSelectAll(source) {
  const checkboxes = document.querySelectorAll(".item-checkbox");
  checkboxes.forEach((checkbox) => {
    checkbox.checked = source.checked;
  });
  updateTotals();
}

function addToCart(menuId) {
  fetch(`/add_to_cart/${menuId}`, {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Item berhasil ditambahkan ke keranjang
        const checkbox = document.getElementById(`checkbox-${menuId}`);
        if (checkbox) {
          checkbox.checked = true; // Centang checkbox
          updateTotals(); // Perbarui total pada halaman
        }
      } else {
        alert(data.message); // Tampilkan pesan kesalahan jika ada
      }
    });
}

document.addEventListener("DOMContentLoaded", function () {
  const navLinks = document.querySelectorAll(".nav-link#kelolaPesanan");
  const cards = document.querySelectorAll(".card[data-status]");
  const messages = document.querySelectorAll("p[data-status]");

  function filterCards(statuses) {
      let hasCards = false;
      cards.forEach((card) => {
          if (statuses.includes(card.getAttribute("data-status"))) {
              card.style.display = "block";
              hasCards = true;
          } else {
              card.style.display = "none";
          }
      });

      messages.forEach((message) => {
          message.style.display = (statuses.includes(message.getAttribute("data-status")) && !hasCards) ? "block" : "none";
      });
  }

  function handleNavClick(event) {
      event.preventDefault();

      navLinks.forEach((nav) => nav.classList.remove("active"));
      this.classList.add("active");

      const status = this.getAttribute("data-status");
      filterCards([status]);
  }

  navLinks.forEach((link) => {
      link.addEventListener("click", handleNavClick);
  });

  filterCards(["menunggu-konfirmasi", "belum-dibayar"]);
});
