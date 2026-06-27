(function () {
    "use strict";

    var workflowOrder = ["farmer", "farm", "flock"];
    var downstreamFilters = {
        farmer: ["farm", "flock"],
        farm: ["flock"],
        flock: [],
    };
    var redirecting = false;

    function filterSelector(name) {
        return '.search-filter[data-name="' + name + '"]';
    }

    function hasWorkflowFilter(name) {
        var control = document.querySelector(filterSelector(name));
        return Boolean(control && control.options.length > 2);
    }

    function hasSelectedWorkflowFilter(name) {
        var control = document.querySelector(filterSelector(name));
        return Boolean(control && control.value);
    }

    function updateQueryForFilter(name, value) {
        if (redirecting) {
            return;
        }

        var url = new URL(window.location.href);
        var params = url.searchParams;

        if (value) {
            params.set(name, value);
        } else {
            params.delete(name);
        }

        (downstreamFilters[name] || []).forEach(function (filterName) {
            params.delete(filterName);
        });

        params.delete("p");

        var queryString = params.toString();
        var nextUrl = url.pathname + (queryString ? "?" + queryString : "");
        var currentUrl = window.location.pathname + window.location.search;

        if (nextUrl === currentUrl) {
            return;
        }

        redirecting = true;
        window.location.assign(nextUrl);
    }

    function bindFilter(name) {
        var control = document.querySelector(filterSelector(name));
        if (!control) {
            return;
        }

        control.dataset.chikoozaAutoFilter = "true";
    }

    function isWorkflowControl(element) {
        return Boolean(
            element &&
            element.classList &&
            element.classList.contains("search-filter") &&
            workflowOrder.indexOf(element.dataset.name) !== -1
        );
    }

    function handleWorkflowChange(element) {
        if (!isWorkflowControl(element)) {
            return;
        }

        updateQueryForFilter(element.dataset.name, element.value);
    }

    function markWaitingFilters() {
        var hasFarmer = hasSelectedWorkflowFilter("farmer");
        var hasFarm = hasSelectedWorkflowFilter("farm");
        var farmFilter = document.querySelector(filterSelector("farm"));
        var flockFilter = document.querySelector(filterSelector("flock"));

        if (farmFilter && !hasFarmer && !hasWorkflowFilter("farm")) {
            farmFilter.closest(".form-group").classList.add("chikooza-filter-waiting");
            farmFilter.closest(".form-group").dataset.waitingText = "Select farmer first";
        }
        if (flockFilter && !hasFarmer && !hasFarm && !hasWorkflowFilter("flock")) {
            flockFilter.closest(".form-group").classList.add("chikooza-filter-waiting");
            flockFilter.closest(".form-group").dataset.waitingText = "Select farmer or farm first";
        }
    }

    function initWorkflowFilters() {
        workflowOrder.forEach(bindFilter);
        markWaitingFilters();
        document.documentElement.dataset.chikoozaAdminFilters = "ready";
    }

    document.addEventListener(
        "change",
        function (event) {
            if (!event.isTrusted) {
                return;
            }

            handleWorkflowChange(event.target);
        },
        true
    );

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initWorkflowFilters);
    } else {
        initWorkflowFilters();
    }

    window.addEventListener("load", function () {
        var $ = window.jQuery || (window.django && window.django.jQuery);
        if (!$) {
            return;
        }

        $(document).on(
            "select2:select select2:clear",
            ".search-filter",
            function () {
                handleWorkflowChange(this);
            }
        );
    });
})();
