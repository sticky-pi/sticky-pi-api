
shinyjs.click_thumbnail_button = function (args) {

    var defaultParams = {
        id : null,
        urls : [null, null, null],
        text: "",
        raw_url:"#",
        annotation_json:"{'annotations':[]}",
        raw_img_width:0
      };
  params = shinyjs.getParams(args, defaultParams);
  const annot_obj = JSON.parse(params.annotation_json);
  console.log("click_thumbnail_button");

  var call = "";
  if(params.urls[0]!= null){
      call = "Shiny.setInputValue('on_clicked_thumbnail_button', {'id':" + params.id + ", 'type': -1})";
      $('#previous_thumbnail_button').attr('onclick', call);
      $('#previous_thumbnail_button').prop('disabled', false);
  }
 else{
    $('#previous_thumbnail_button').prop('disabled', true);
 }

  if(params.urls[2] != null){
      call = "Shiny.setInputValue('on_clicked_thumbnail_button', {'id':" + params.id + ", 'type': 1})";
      $('#next_thumbnail_button').attr('onclick', call);
      $('#next_thumbnail_button').prop('disabled', false);
 }
 else{
    $('#next_thumbnail_button').prop('disabled', true);
 }

  $('a#current_thumbnail').attr('href', params.raw_url);
  $('img#previous_thumbnail').attr('src', params.urls[0]);
  $('canvas#current_thumbnail').css('background', 'url(' +  params.urls[1] + ')');
  $('canvas#current_thumbnail').css('background-size', '100% 100%');
  $('img#next_thumbnail').attr('src', params.urls[2]);
  $('div#thumbnail_modal_text').html(params.text);


  // draw actual annotations on the client side
  //var ctx = canvas.getContext("2d");
  var ctx =  $("canvas#current_thumbnail")[0].getContext('2d');
  ctx.clearRect(0, 0, $("canvas#current_thumbnail")[0].width, $("canvas#current_thumbnail")[0].height);
  if(params.raw_img_width == 0 || annot_obj === null)
    return null;
  ctx.lineWidth = 5;
  var raw_img_width = params.raw_img_width;
  // fixme this number is hard-coding the dimension of the canvas
  var ratio = raw_img_width/ 1200;
  console.log(ratio);
  ;
  for(j in annot_obj.annotations){
      var a = annot_obj.annotations[j];
      if(a.contour.length >2){
          ctx.strokeStyle = a.stroke_colour;
          ctx.beginPath();
          ctx.moveTo(a.contour[0][0][0]/ratio, a.contour[0][0][1]/ratio);
          for(i=1; i != a.contour.length; i++){
            ctx.lineTo(a.contour[i][0][0]/ratio, a.contour[i][0][1]/ratio);
          }
          // close the path
          ctx.lineTo(a.contour[0][0][0]/ratio, a.contour[0][0][1]/ratio);
          ctx.stroke();
        }
    }
}

var play_thumbnails_timer = null;

shinyjs.play_pause_thumbnail_button = function (play=true, interval=500) {

  if(play){
    clearInterval(play_thumbnails_timer);
    play_thumbnails_timer = setInterval(
                                    function(){
                                        $('#next_thumbnail_button').click();
                                     },
                                     interval);
    $('#pause_thumbnail_button').show();
    $('#play_thumbnail_button').hide();

   }
  else{
    clearInterval(play_thumbnails_timer);
    $('#play_thumbnail_button').show();
    $('#pause_thumbnail_button').hide();
    }

}



shinyjs.copy_to_clipboard = function() {
    var $temp = $("<input>");
    $("#thumbnail_images").append($temp);
    $temp.val($(image_ID).text()).select();
    document.execCommand("copy");
    $temp.remove();
    }