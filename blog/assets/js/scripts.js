// A $( document ).ready() block.
$( document ).ready(function() {

	// DropCap.js
	var dropcaps = document.querySelectorAll(".dropcap");
	window.Dropcap.layout(dropcaps, 2);

	// Responsive-Nav
	var nav = responsiveNav(".nav-collapse");

	// Round Reading Time
    $(".time").text(function (index, value) {
      return Math.round(parseFloat(value));
    });

	// Comment Form AJAX Submission
	$("#comment-form").on("submit", function(e) {
		e.preventDefault();
		
		var form = $(this);
		var formData = form.serialize();
		var submitButton = $("#comment-submit");
		
		// Disable submit button and show loading state
		submitButton.prop("disabled", true).text("Submitting...");
		
		// Hide any previous success/error messages
		$("#comment-success, #comment-error").hide();
		
		$.ajax({
			url: form.attr("action"),
			type: "POST",
			data: formData,
			success: function(response) {
				// Hide the form and show success message
				form.hide();
				$("#comment-success").show();
			},
			error: function(xhr, status, error) {
				// Show error message and re-enable form
				$("#comment-error").show();
				submitButton.prop("disabled", false).text("Submit Comment");
			}
		});
	});

});


