var Exercise = Backbone.Model.extend({
});

var ExerciseCollection = Backbone.Collection.extend({
    model: Exercise
});

var ExerciseFilterView = Backbone.View.extend({
    initialize: function(el, collection){
        this.template = _.template($("#exercise-filter-view").html());
        this.$el = el;
        this.collection = collection;
        this.allEquipment = JSContext.equipment;
        this.allMuscleGroups = JSContext.muscle_groups;
        this.allExerciseTypes = JSContext.exercise_types;
        console.log(this.allEquipment);
    },
    render: function(){
        var renderData = {
            muscleGroups: this.allMuscleGroups
        };
        this.$el.html(this.template(renderData));
        return this;
    }
});
