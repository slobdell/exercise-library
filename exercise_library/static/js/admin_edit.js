var AdminEditView = Backbone.View.extend({
    events: {
        "click .save": "saveExercise"
    },
    initialize: function(exerciseModel){
        this.template = _.template($("#admin-edit-view").html());
        this.exerciseModel = exerciseModel;
    },
    _getExerciseTypes: function(){
        var selector = this.$(".exercise-type-checks");
        var typeIds = [];
        for(var i=0; i<selector.length; i++){
            var item = selector[i];
            var inputId = item.id;
            var exerciseTypeId = inputId.split("exercise-type-")[1];
            exerciseTypeId = parseInt(exerciseTypeId, 10);
            typeIds.push(exerciseTypeId);
        }
        return typeIds;
    },
    saveExercise: function(){
        var postData = {
            name: $.trim(this.$(".exercise-name").val()),
            video_id: $.trim(this.$(".video-id").val()),
            compound: this.$("#compound-true").is(":checked") ? 1: 0,
            exercise_type_ids: this._getExerciseTypes(),
            min_experience_id: parseInt(this.$(".experience-value").val(), 10),
            min_fitness_level_id: parseInt(this.$(".fitness-value").val(), 10),
            one_limb: this.$("#one-limb-false").is(":checked") ? 0: 1,
            timed: null,
            equipment_ids: null,
            phase_ids: null,
            workout_component_id: null,
            mutually_exclusive: null,
            muscle_group_id: null,
            secondary_muscle_group_id: null,
        };
    },
    _getOrCreateEl: function(){
        if ($(".modal-parent").length === 0){
            $("body").append(
                "<div class='modal-parent'></div>"
            );
        }
        this.$el = $(".modal-parent");
    },
    delegateTypeAhead: function(){
        $(".typeahead").typeahead({
            source: _.debounce(function(query, process){
    var url = "/api/autocomplete/?q=" + query.toLowerCase();
                return $.get(url, function(data){
                    // data is the raw response from the API
                    return process(data);
                });
            }, 100),
            matcher: function(item){
                // needed in order to allow typos
                return true;
            },
            items: 10,
            minLength: 1
        });
    },
    render: function(){
        this._getOrCreateEl();
        var mutexName = null;
        if(this.exerciseModel.get("mutually_exclusive")) {
            for(var i=0; i<JSContext.exercises.length; i++){
                var otherExercise = JSContext.exercises[i];
                if(otherExercise.id === this.exerciseModel.get("mutually_exclusive")){
                    mutexName = otherExercise.name;
                    break;
                }
            }
        }
        var renderData = {
            "exercise": this.exerciseModel.toJSON(),
            "equipment": JSContext.equipment,
            "muscleGroups": JSContext.muscle_groups,
            "phases": JSContext.phases,
            "workoutComponents": JSContext.workout_components,
            "mutexName": mutexName,
            "exerciseTypes": JSContext.exercise_types
        }
        console.log(renderData);
        this.$el.html(this.template(renderData));
        this.$("#myModal").modal();
        this.delegateTypeAhead();
        this.delegateEvents();
    }
});
