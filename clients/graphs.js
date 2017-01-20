/////////////////////////////////////
///      GRAPHS
/////////////////////////////////////

function displayGraphExample(id,channel,representation) {
   var graph = d3.select(id).append("svg:svg")
              .attr("width", width)
              .attr("height", height);
   g = graph.append("g").attr("transform","translate(" + margin.left + "," + margin.top + ")");
    var width1 = +width - margin.left - margin.right,
    height1 = +height - margin.top - margin.bottom;
   g.append("defs").append("clipPath")
    .attr("id", "clip")
    .append("rect")
    .attr("width", width1)
    .attr("height", height1);
   g.append("g")
    .attr("class", "axis axis--x")
    .attr("transform", "translate(0," + y(0) + ")")
    .call(d3.axisBottom(x));

   g.append("g")
      .attr("clip-path", "url(#clip)")
    myLine = g.append("path")
    .datum(d3.range(n).map(function(){return 1;})) //Initial data
    .attr("class", "line")
    .attr("d",representation);
    graph.append("text")
         .attr("class","channel_name")
         .attr("dy", "1em").attr("text-anchor", "start")
         .text(channel);
    graph.append("text")
         .attr("transform", "translate(" + x(n*1.03) + "," + y(2.5) +")")
         .attr("class","final_value")
         .attr("text-anchor", "start")
         .text(channel);

   return myLine;
  }

function redrawWithoutAnimation(myLine, myData, myRepresentation) {
            // static update without animation
            myLine.data([myData]) // set the new data
                .attr("d", myRepresentation); // apply the new data values
            d3.select(myLine.node().parentElement.parentElement.lastChild)
               .text(myData[n-1].toFixed(2));
        }
