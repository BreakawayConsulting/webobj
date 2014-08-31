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
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/flub/start", false);
        xhr.send('{}');
    },

    flubStop: function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/flub/stop", false);
        xhr.send('{}');
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
