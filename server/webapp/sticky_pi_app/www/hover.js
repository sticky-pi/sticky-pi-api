function(el, x) {
  el.on('plotly_click', function(d) {
  if(d.event.button === 0){ // left click
    var point = d.points[0];
    var key = point.data.key[point.pointIndex];
    Shiny.onInputChange('on_clicked_plot', {'key': key});
    }
  });
  el.on('plotly_unhover', function(d) {
    var key = -1;
    Shiny.onInputChange('thumbnail_mini_to_fetch', {'key': key,
      'hov_x': d.event.clientX,
      'hov_y': d.event.clientY});
  });

  el.on('plotly_hover', function(d) {
    var point = d.points[0];
    var key = point.data.key[point.pointIndex];
    $('div#time_plot_tooltip').css({left: d.event.pageX +"px",
                                    top: d.event.pageY + "px",
                                     visibility:'visible'});


    Shiny.onInputChange('thumbnail_mini_to_fetch', {'key': key,
    'hov_x': d.event.clientX,
    'hov_y': d.event.clientY});
  });
}
