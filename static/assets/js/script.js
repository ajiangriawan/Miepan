function wcqib_refresh_quantity_increments() {
  jQuery(
    "div.quantity:not(.buttons_added), td.quantity:not(.buttons_added)"
  ).each(function (a, b) {
    var c = jQuery(b);
    c.addClass("buttons_added"),
      c
        .children()
        .first()
        .before('<input type="button" value="-" class="minus" />'),
      c
        .children()
        .last()
        .after('<input type="button" value="+" class="plus" />');
  });
}

String.prototype.getDecimals ||
  (String.prototype.getDecimals = function () {
    var a = this,
      b = ("" + a).match(/(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/);
    return b ? Math.max(0, (b[1] ? b[1].length : 0) - (b[2] ? +b[2] : 0)) : 0;
  }),
  jQuery(document).ready(function () {
    wcqib_refresh_quantity_increments();
  }),
  jQuery(document).on("updated_wc_div", function () {
    wcqib_refresh_quantity_increments();
  }),
  jQuery(document).on("click", ".plus, .minus", function () {
    var a = jQuery(this).closest(".quantity").find(".qty"),
      b = parseFloat(a.val()),
      c = parseFloat(a.attr("max")),
      d = parseFloat(a.attr("min")),
      e = a.attr("step");
    (b && "" !== b && "NaN" !== b) || (b = 0),
      ("" !== c && "NaN" !== c) || (c = ""),
      ("" !== d && "NaN" !== d) || (d = 0),
      ("any" !== e && "" !== e && void 0 !== e && "NaN" !== parseFloat(e)) ||
        (e = 1),
      jQuery(this).is(".plus")
        ? c && b >= c
          ? a.val(c)
          : a.val((b + parseFloat(e)).toFixed(e.getDecimals()))
        : d && b <= d
        ? a.val(d)
        : b > 0 && a.val((b - parseFloat(e)).toFixed(e.getDecimals())),
      a.trigger("change");
  });

document.addEventListener("DOMContentLoaded", function () {
  const navLinks = document.querySelectorAll(".nav-link#pesanan");
  const cards = document.querySelectorAll(".card[data-status]");

  function filterCards(status) {
    cards.forEach((card) => {
      card.style.display =
        card.getAttribute("data-status") === status ? "block" : "none";
    });
  }

  function handleNavClick(event) {
    event.preventDefault();

    navLinks.forEach((nav) => nav.classList.remove("active"));
    this.classList.add("active");

    const status = this.getAttribute("data-status");
    filterCards(status);
  }

  navLinks.forEach((link) => {
    link.addEventListener("click", handleNavClick);
  });

  filterCards("belum-dibayar");
});

document.addEventListener("DOMContentLoaded", function () {
  const navLinks = document.querySelectorAll(".nav-link#kelolaPesanan");
  const cards = document.querySelectorAll(".card[data-status]");

  function filterCards(status) {
    cards.forEach((card) => {
      card.style.display =
        card.getAttribute("data-status") === status ? "block" : "none";
    });
  }

  function handleNavClick(event) {
    event.preventDefault();

    navLinks.forEach((nav) => nav.classList.remove("active"));
    this.classList.add("active");

    const status = this.getAttribute("data-status");
    filterCards(status);
  }

  navLinks.forEach((link) => {
    link.addEventListener("click", handleNavClick);
  });

  filterCards("cek");
});

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

document.addEventListener('DOMContentLoaded', function() {
  fetch('/cart_count')
      .then(response => response.json())
      .then(data => {
          if (data.total_items !== undefined) {
              document.getElementById('total_cart').innerText = data.total_items;
          }
      })
      .catch(error => console.error('Error fetching cart count:', error));
});