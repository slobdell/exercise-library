var AdminEditView = Backbone.View.extend({
    events: {
        "click .save": "saveExercise"
    },
    initialize: function(exerciseModel){
        this.template = _.template($("#admin-edit-view").html());
        this.exerciseModel = exerciseModel;
    },
    _getExerciseTypes: function(){
        var selector = this.$(".exercise-type-checks:checked");
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
    _getCheckedEquipment: function(){
        var selector = this.$(".equipment-type-checks:checked");
        var equipmentIds = [];
        for(var i=0; i<selector.length; i++){
            var item = selector[i];
            var inputId = item.id;
            var equipmentId = inputId.split("equipment-")[1];
            equipmentId = parseInt(equipmentId, 10);
            equipmentIds.push(equipmentId);
        }
        return equipmentIds;
    },
    _getCheckedPhases: function(){
        var selector = this.$(".phase-checks:checked");
        var phaseIds = [];
        for(var i=0; i<selector.length; i++){
            var item = selector[i];
            var inputId = item.id;
            var phaseId = inputId.split("phase-")[1];
            phaseId = parseInt(phaseId, 10);
            phaseIds.push(phaseId);
        }
        return phaseIds;
    },
    _getSecondaryMuscles: function(){
        var muscleIds = [];
        var selector = this.$(".muscle-checks:checked");
        for(var i=0; i<selector.length; i++){
            var item = selector[i];
            var inputId = item.id;
            var muscleId = inputId.split("secondary-muscle-")[1];
            muscleId = parseInt(muscleId, 10);
            muscleIds.push(muscleId);
        }
        return muscleIds;
    },
    exerciseIdFromText: function(){
        var searchText = this.$(".typeahead").val();
        var self = this;
        searchText = searchText.toLowerCase();
        $.get("/api/exercise/?exercise=" + searchText, function(exerciseResponse){
            var exerciseId = exerciseResponse.id;
            self.postExerciseData(exerciseId);
        });
    },
    postExerciseData: function(mutuallyExclusiveId){
        // TODO need to handle case for new exercise
        var postData = {
            id: this.exerciseModel.get("id"),
            name: $.trim(this.$(".exercise-name").val()),
            video_id: $.trim(this.$(".video-id").val()),
            compound: this.$("#compound-true").is(":checked") ? 1: 0,
            exercise_type_ids: this._getExerciseTypes(),
            min_experience_id: parseInt(this.$(".experience-value").val(), 10),
            min_fitness_level_id: parseInt(this.$(".fitness-value").val(), 10),
            one_limb: this.$("#one-limb-false").is(":checked") ? 0: 1,
            timed: this.$("#timed-false").is(":checked") ? 0: 1,
            equipment_ids: this._getCheckedEquipment(),
            phase_ids: this._getCheckedPhases(),
            workout_component_id: parseInt(this.$(".workout-component-value").val(), 10),
            mutually_exclusive: mutuallyExclusiveId,
            muscle_group_id: parseInt(this.$("input[name='primary-muscle']:checked")[0].id.split("muscle-")[1], 10),
            secondary_muscle_group_id: this._getSecondaryMuscles(),
        };
        this._post(postData);
    },
    _post: function(postData){
        $.ajax({
            url: '/api/save/',
            data: postData,
            cache: false,
            dataType: 'json',
            traditional: true,
            type: 'POST',
            contentType: 'application/x-www-form-urlencoded;charset=utf-8',
            success: function(response){
                alert("success");
            },
            error: function(data){
                alert("error");
            }
        });
    },
    saveExercise: function(){
        if(this.$(".typeahead").val()){
            this.exerciseIdFromText();
        } else {
            this.postExerciseData(null);
        }
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
