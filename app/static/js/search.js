// Adapted from http://jsfiddle.net/ukW2C/3/
$("#search").keyup(function () {
      //split the current value of search
      var data = this.value.split(" ");

      //create a jquery object of the rows
      var jo = $("#users").find("tr");
      if (this.value == "") {
                jo.show();
                $("#search-group").removeClass("has-error");
                $("#search-group").removeClass("has-success");
                return;
            }
      //hide all the rows
      jo.hide();

      //Recusively filter the jquery object to get results.
      filtered = jo.filter(function (i, v) {
                var $t = $(this);
                for (var d = 0; d < data.length; ++d) {
                              if ($t.is(":contains('" + data[d] + "')")) {
                                                return true;
                                            }
                          }
                return false;
            });
      //show the rows that match.
      filtered.show();

      //update the search bar validation status
      if (filtered.length) {
        $("#search-group").addClass("has-success");
        $("#search-group").removeClass("has-error");
      } else {
        $("#search-group").addClass("has-error");
        $("#search-group").removeClass("has-success");
      }
}).focus(function () {
      this.value = "";
      $(this).unbind('focus');
});
