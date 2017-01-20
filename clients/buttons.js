/////////////////////////////////////
///      BUTTONS
/////////////////////////////////////
function button_toggle(thisButton){
  //console.log(thisButton);
  var AmIOn = thisButton.classed("disabled");
  thisButton.classed("disabled",AmIOn ? false : true);
  send_data_back(thisButton.ref,thisButton.pinNumber,+AmIOn);

  console.log(['Button pushed',thisButton.ref,thisButton.pinNumber,+AmIOn]);
}

function button_value(thisButton,value){
  thisButton.classed("disabled",!value);
  send_data_back(thisButton.ref,thisButton.pinNumber,+value);
  //console.log("Button "+ thisButton.pinNumber + value);
}

function button_on(thisButton){
  button_value(thisButton,1);
};

function button_off(thisButton){
  button_value(thisButton,0);
};

function makeButton(ref,pinNumber, containerID){
   var buttonSVG = d3.select(containerID).append("svg:svg")
   .attr("width", 30)
   .attr("height", 60);
   var myButton = buttonSVG.append("rect")
          .attr("x",5)
          .attr("y",5)
          .attr("rx", 4)
          .attr("ry", 4)
          .attr("width", 20)
          .attr("height",20)
          .attr("class","button")
          .classed("disabled",true)
          .classed(ref,true)
          .attr("pinNumber",pinNumber)
          .attr("ref",ref)
          .on("click", function() {
            var AmIOn = d3.select(this).classed("disabled");
            d3.select(this).classed("disabled",AmIOn ? false : true);
            send_data_back(ref,pinNumber,+AmIOn);//);
   });
   var myText = buttonSVG.append("text")
          .attr("x",5)
          .attr("y",60)
          .attr("class","button text")
          .attr("dy", "-1em")
          .text(pinNumber);

   myButton.ref=ref;
   myButton.pinNumber=pinNumber;

   return myButton;
   }
