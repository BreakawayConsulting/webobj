var Flub = React.createClass({
    getInitialState: function() {
        return {'bar': null};
    },

    componentWillMount: function() {
        var feed = new EventSource("/flub+events");
        feed.addEventListener("message", this.eventMsg, false);
    },

    eventMsg: function(msg) {
        var flubState = JSON.parse(msg.data);
        this.setState(flubState);
    },

    flubStart: function(e) {
        console.log("flubStart");
    },

    flubStop: function(e) {
        console.log("flubStop");
    },

    render: function() {
        return React.DOM.div({},
                             React.DOM.p({}, 'Hello, Flub! Current count: ' + this.state.bar),
                             React.DOM.button({'onClick': this.flubStop}, 'Stop!'),
                             React.DOM.button({'onClick': this.flubStart}, 'Start!')
                            );
    }
});

React.renderComponent(Flub(), document.body);
